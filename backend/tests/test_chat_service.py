"""
智能问答服务测试。

测试目标：
  - _rag_retrieve：向量检索，含降级（API 不可用时返回空列表）
  - send_message：主流程（RAG + MiniMax），含 _save_ctx 结构
  - save_messages：后台任务写入，含异常回滚

外部依赖（MiniMax API、向量库）全部 Mock，测试不产生任何网络请求。
"""
import uuid

import pytest

from app.services import chat_service
from app.models.chat import ChatMessage


# ─────────────────────────────────────────────────────────────
# _rag_retrieve 测试
# ─────────────────────────────────────────────────────────────

class TestRagRetrieve:
    def test_returns_results_when_embedding_succeeds(self, db, mocker):
        """Embedding 和向量库都正常时，返回检索结果列表。"""
        fake_embedding = [0.1] * 1536
        fake_refs = [
            {"section_id": "s1", "section_title": "第一章", "file_name": "ch1.pdf",
             "excerpt": "进程状态转换的内容...", "score": 0.91},
        ]
        mocker.patch("app.services.minimax_client.embed_query", return_value=fake_embedding)
        mocker.patch("app.db.vector_store.query_chunks", return_value=fake_refs)

        result = chat_service._rag_retrieve("course_1", None, "进程状态怎么转换？", db)
        assert result == fake_refs

    def test_filters_by_section_id_when_provided(self, db, mocker):
        """指定 section_id 时，只保留该小节的检索结果。"""
        fake_embedding = [0.1] * 1536
        fake_refs = [
            {"section_id": "s1", "section_title": "第一章", "file_name": "ch1.pdf",
             "excerpt": "第一章内容", "score": 0.9},
            {"section_id": "s2", "section_title": "第二章", "file_name": "ch2.pdf",
             "excerpt": "第二章内容", "score": 0.85},
        ]
        mocker.patch("app.services.minimax_client.embed_query", return_value=fake_embedding)
        mocker.patch("app.db.vector_store.query_chunks", return_value=fake_refs)

        result = chat_service._rag_retrieve("course_1", "s1", "问题", db)
        assert len(result) == 1
        assert result[0]["section_id"] == "s1"

    def test_returns_empty_when_embedding_fails(self, db, mocker):
        """Embedding API 异常时，静默降级返回空列表，不抛出异常。"""
        mocker.patch(
            "app.services.minimax_client.embed_query",
            side_effect=RuntimeError("API 不可用"),
        )
        result = chat_service._rag_retrieve("course_1", None, "问题", db)
        assert result == []

    def test_returns_empty_when_vector_store_fails(self, db, mocker):
        """向量库查询异常时，静默降级返回空列表。"""
        mocker.patch("app.services.minimax_client.embed_query", return_value=[0.1] * 1536)
        mocker.patch(
            "app.db.vector_store.query_chunks",
            side_effect=Exception("向量库连接失败"),
        )
        result = chat_service._rag_retrieve("course_1", None, "问题", db)
        assert result == []

    def test_returns_empty_list_when_no_results(self, db, mocker):
        """向量库无结果时返回空列表。"""
        mocker.patch("app.services.minimax_client.embed_query", return_value=[0.0] * 1536)
        mocker.patch("app.db.vector_store.query_chunks", return_value=[])

        result = chat_service._rag_retrieve("course_1", None, "问题", db)
        assert result == []


# ─────────────────────────────────────────────────────────────
# send_message 测试
# ─────────────────────────────────────────────────────────────

class TestSendMessage:
    def _setup_enrolled_student(self, db, make_user, make_course, enroll):
        """创建一个已加入课程的学生，返回 (student, course)。"""
        teacher = make_user(role="teacher")
        student = make_user(role="student")
        course = make_course(teacher_id=teacher.id)
        enroll(course.id, student.id)
        return student, course

    def test_send_message_returns_answer(self, db, make_user, make_course, enroll, mocker):
        """正常调用返回 answer、session_id、rag_used 等字段。"""
        student, course = self._setup_enrolled_student(db, make_user, make_course, enroll)
        mocker.patch("app.services.minimax_client.embed_query", return_value=[0.1] * 1536)
        mocker.patch("app.db.vector_store.query_chunks", return_value=[])
        mocker.patch(
            "app.services.minimax_client.answer_question",
            return_value={"answer": "进程有五种状态。", "suggestions": ["复习课件第一章"]},
        )

        result = chat_service.send_message(
            course_id=course.id,
            student_id=student.id,
            question="进程有哪些状态？",
            session_id=None,
            section_id=None,
            db=db,
        )
        assert result["answer"] == "进程有五种状态。"
        assert "session_id" in result
        assert result["rag_used"] is False
        assert result["suggestions"] == ["复习课件第一章"]

    def test_send_message_includes_save_ctx(self, db, make_user, make_course, enroll, mocker):
        """返回值必须包含 _save_ctx，且包含写入所需的全部字段。"""
        student, course = self._setup_enrolled_student(db, make_user, make_course, enroll)
        mocker.patch("app.services.minimax_client.embed_query", return_value=[0.1] * 1536)
        mocker.patch("app.db.vector_store.query_chunks", return_value=[])
        mocker.patch(
            "app.services.minimax_client.answer_question",
            return_value={"answer": "回答内容", "suggestions": []},
        )

        result = chat_service.send_message(
            course_id=course.id,
            student_id=student.id,
            question="测试问题",
            session_id=None,
            section_id=None,
            db=db,
        )
        ctx = result.get("_save_ctx")
        assert ctx is not None, "必须包含 _save_ctx 字段"
        assert ctx["student_id"] == student.id
        assert ctx["course_id"] == course.id
        assert ctx["question"] == "测试问题"
        assert "answer" in ctx

    def test_send_message_rag_used_true_when_refs_exist(self, db, make_user, make_course, enroll, mocker):
        """检索到结果时，rag_used 应为 True，references 应包含结果。"""
        student, course = self._setup_enrolled_student(db, make_user, make_course, enroll)
        fake_refs = [
            {"section_id": "s1", "section_title": "第一章", "file_name": "ch1.pdf",
             "excerpt": "进程状态说明", "score": 0.9},
        ]
        mocker.patch("app.services.minimax_client.embed_query", return_value=[0.1] * 1536)
        mocker.patch("app.db.vector_store.query_chunks", return_value=fake_refs)
        mocker.patch(
            "app.services.minimax_client.answer_question",
            return_value={"answer": "基于课件的回答", "suggestions": []},
        )

        result = chat_service.send_message(
            course_id=course.id,
            student_id=student.id,
            question="状态转换问题",
            session_id=None,
            section_id=None,
            db=db,
        )
        assert result["rag_used"] is True
        assert len(result["references"]) == 1

    def test_send_message_uses_provided_session_id(self, db, make_user, make_course, enroll, mocker):
        """如果提供了 session_id，返回值中的 session_id 应与输入一致。"""
        student, course = self._setup_enrolled_student(db, make_user, make_course, enroll)
        mocker.patch("app.services.minimax_client.embed_query", return_value=[0.1] * 1536)
        mocker.patch("app.db.vector_store.query_chunks", return_value=[])
        mocker.patch(
            "app.services.minimax_client.answer_question",
            return_value={"answer": "回答", "suggestions": []},
        )

        fixed_session_id = str(uuid.uuid4())
        result = chat_service.send_message(
            course_id=course.id,
            student_id=student.id,
            question="问题",
            session_id=fixed_session_id,
            section_id=None,
            db=db,
        )
        assert result["session_id"] == fixed_session_id

    def test_send_message_loads_history(self, db, make_user, make_course, enroll, mocker):
        """已有会话历史时，应传给 MiniMax（验证 answer_question 被调用时包含历史参数）。"""
        student, course = self._setup_enrolled_student(db, make_user, make_course, enroll)
        session_id = str(uuid.uuid4())
        # 预置一条历史消息
        db.add(ChatMessage(
            user_id=student.id, session_id=session_id,
            course_id=course.id, section_id=None,
            role="user", content="上一个问题",
        ))
        db.commit()

        mocker.patch("app.services.minimax_client.embed_query", return_value=[0.1] * 1536)
        mocker.patch("app.db.vector_store.query_chunks", return_value=[])
        mock_answer = mocker.patch(
            "app.services.minimax_client.answer_question",
            return_value={"answer": "带历史的回答", "suggestions": []},
        )

        chat_service.send_message(
            course_id=course.id,
            student_id=student.id,
            question="新问题",
            session_id=session_id,
            section_id=None,
            db=db,
        )
        # 验证调用时传入了历史（第三个位置参数 history 不为空）
        call_args = mock_answer.call_args
        history_arg = call_args[0][2]  # answer_question(question, course, history, context)
        assert len(history_arg) >= 1

    def test_send_message_raises_404_if_not_enrolled(self, db, make_user, make_course):
        """未加入课程的学生调用应抛出 HTTPException 404/403。"""
        from fastapi import HTTPException
        teacher = make_user(role="teacher")
        student = make_user(role="student")
        course = make_course(teacher_id=teacher.id)
        # 没有 enroll

        with pytest.raises(HTTPException):
            chat_service.send_message(
                course_id=course.id,
                student_id=student.id,
                question="问题",
                session_id=None,
                section_id=None,
                db=db,
            )


# ─────────────────────────────────────────────────────────────
# save_messages 测试
# ─────────────────────────────────────────────────────────────

class TestSaveMessages:
    def test_save_messages_writes_two_records(self, db, mocker):
        """正常调用应向数据库写入用户消息和 AI 回答两条记录。"""
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        course_id = str(uuid.uuid4())

        # 用 db fixture 的 engine 替换 app.db.session.SessionLocal
        from sqlalchemy.orm import sessionmaker
        SessionMock = sessionmaker(bind=db.get_bind())

        mocker.patch(
            "app.db.session.SessionLocal",
            return_value=SessionMock(),
        )

        ctx = {
            "student_id": user_id,
            "course_id": course_id,
            "section_id": None,
            "question": "问题文本",
            "answer": "AI 回答文本",
        }
        chat_service.save_messages(session_id, ctx)

        records = db.query(ChatMessage).filter(ChatMessage.session_id == session_id).all()
        assert len(records) == 2
        roles = {r.role for r in records}
        assert "user" in roles
        assert "assistant" in roles

    def test_save_messages_content_correct(self, db, mocker):
        """写入的消息内容应与 ctx 一致。"""
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        from sqlalchemy.orm import sessionmaker
        SessionMock = sessionmaker(bind=db.get_bind())
        mocker.patch("app.db.session.SessionLocal", return_value=SessionMock())

        ctx = {
            "student_id": user_id,
            "course_id": "c1",
            "section_id": "s1",
            "question": "什么是进程？",
            "answer": "进程是正在运行的程序实例。",
        }
        chat_service.save_messages(session_id, ctx)

        user_msg = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id,
            ChatMessage.role == "user",
        ).first()
        ai_msg = db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id,
            ChatMessage.role == "assistant",
        ).first()
        assert user_msg.content == "什么是进程？"
        assert ai_msg.content == "进程是正在运行的程序实例。"
        assert user_msg.section_id == "s1"

    def test_save_messages_handles_db_exception_gracefully(self, db, mocker):
        """数据库写入异常时，save_messages 应静默记录日志，不向外抛出异常。"""
        broken_session = mocker.MagicMock()
        broken_session.__enter__ = mocker.MagicMock(return_value=broken_session)
        broken_session.__exit__ = mocker.MagicMock(return_value=False)
        broken_session.add.side_effect = Exception("DB 连接断开")
        broken_session.rollback = mocker.MagicMock()
        broken_session.close = mocker.MagicMock()
        mocker.patch("app.db.session.SessionLocal", return_value=broken_session)

        ctx = {
            "student_id": "u1", "course_id": "c1", "section_id": None,
            "question": "问题", "answer": "回答",
        }
        # 不应抛出异常
        chat_service.save_messages("session_x", ctx)
        broken_session.rollback.assert_called_once()
