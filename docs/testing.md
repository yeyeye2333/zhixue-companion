# 测试文档

本文档记录智学伴侣后端的测试范围、各测试用例的测试目标、预期行为与实际结果，并给出整体覆盖评估。

---

## 1. 测试总览

### 1.1 执行环境

| 项目 | 值 |
|---|---|
| Python | 3.11.11 |
| pytest | 9.0.3 |
| pytest-mock | 3.15.1 |
| 数据库 | 内存 SQLite（每个测试函数独立实例，互不污染） |
| 外部依赖 | 全部 Mock（MiniMax API、ChromaDB、pgvector 均不发起真实网络请求） |
| 运行命令 | `uv run pytest tests/ -v`（在 `backend/` 目录下执行） |

### 1.2 汇总结果

| 测试文件 | 用例数 | 通过 | 失败 | 通过率 |
|---|---|---|---|---|
| `test_text_chunking.py` | 23 | 23 | 0 | 100% |
| `test_vector_utils.py` | 16 | 16 | 0 | 100% |
| `test_quiz_grading.py` | 22 | 22 | 0 | 100% |
| `test_chat_service.py` | 14 | 14 | 0 | 100% |
| `test_learning_plan_service.py` | 26 | 26 | 0 | 100% |
| **合计** | **101** | **101** | **0** | **100%** |

最近一次完整运行耗时：**11.86 秒**

---

## 2. 测试基础设施

### 2.1 公共 Fixture（`conftest.py`）

所有测试共享以下 Fixture，无需在每个测试文件中重复搭建。

| Fixture | 作用 |
|---|---|
| `db` | 创建内存 SQLite 数据库，自动建表、测试结束后自动销毁，作用域为函数级（每个测试独立） |
| `make_user` | 工厂函数，接受 `role`（student/teacher）和 `extra` 参数，创建用户并写入数据库 |
| `make_course` | 工厂函数，根据 `teacher_id` 创建课程 |
| `enroll` | 将学生加入课程，创建 `CourseEnrollment` 记录 |

### 2.2 Mock 策略

测试不依赖任何外部服务，Mock 目标统一为：

| Mock 路径 | 替代的真实行为 |
|---|---|
| `app.services.minimax_client.embed_query` | MiniMax Embedding API 调用 |
| `app.services.minimax_client.embed_texts` | 批量 Embedding API 调用 |
| `app.services.minimax_client.answer_question` | MiniMax 问答 API 调用 |
| `app.services.minimax_client.generate_learning_plan` | MiniMax 计划生成 API 调用 |
| `app.services.minimax_client.adjust_learning_plan` | MiniMax 计划调整 API 调用 |
| `app.db.vector_store.query_chunks` | 向量数据库相似度检索 |
| `app.db.session.SessionLocal` | 数据库 Session 工厂（用于后台任务测试） |
| `app.services.quiz_service.get_quiz_scores_for_signals` | 测试成绩信号查询 |

---

## 3. 文本分块测试（`test_text_chunking.py`）

**被测模块**：`app/services/section_service.py`

**被测函数**：`_split_text`、`_char_split`、`_text_hash`

**背景**：教师上传课件后，系统需要将提取的文本切分为若干块（chunk）再向量化写入向量库。分块质量直接影响 RAG 检索的语义准确性。当前采用段落/标题感知策略：优先在 Markdown 标题行（`#` 开头）和连续空行处切分，超长段落再降级为字符级分块；同时引入 SHA-256 hash 对比，内容未变时跳过重建索引。

### 3.1 字符级降级分块（`_char_split`）

| # | 测试名 | 测试目标 | 预期结果 | 实际结果 |
|---|---|---|---|---|
| 1 | `test_empty_text_returns_empty` | 空字符串输入 | 返回空列表 `[]` | ✅ 通过 |
| 2 | `test_short_text_returns_single_chunk` | 短于阈值（500 字）的文本 | 返回仅含原文本的单元素列表 | ✅ 通过 |
| 3 | `test_long_text_splits_into_multiple_chunks` | 长度为 1500 字的均匀文本 | 分出超过 1 个块 | ✅ 通过 |
| 4 | `test_all_chunks_within_max_size` | 每个块的长度上限 | 所有块长度 ≤ `_CHUNK_SIZE × 1.5`（允许在句子边界略微超出） | ✅ 通过 |
| 5 | `test_splits_at_sentence_boundary` | 句号处优先断开 | 超过 50% 的块以中文句号或英文句号结尾 | ✅ 通过 |
| 6 | `test_no_empty_chunks` | 不产生空块 | 返回列表中无空字符串 | ✅ 通过 |

### 3.2 段落/标题感知主分块策略（`_split_text`）

| # | 测试名 | 测试目标 | 预期结果 | 实际结果 |
|---|---|---|---|---|
| 7 | `test_empty_text_returns_empty` | 空字符串输入 | 返回空列表 | ✅ 通过 |
| 8 | `test_short_text_kept_as_single_chunk` | 无空行无标题的短文本 | 整体作为一个块返回 | ✅ 通过 |
| 9 | `test_splits_on_blank_lines` | 两段落间有空行 | 切出 2 个块，各含原段落内容 | ✅ 通过 |
| 10 | `test_splits_on_markdown_headings` | 含 `## 标题` 的文本 | 至少切出 3 块（引言、一节、二节），标题内容保留在块中 | ✅ 通过 |
| 11 | `test_multiple_blank_lines_treated_as_one_separator` | 4 个连续空行 | 等同于 1 个段落分隔，切出 2 块 | ✅ 通过 |
| 12 | `test_long_paragraph_gets_further_split` | 单段落超过 500 字（约 1100 字） | 触发字符级降级分块，切出多于 1 块 | ✅ 通过 |
| 13 | `test_preserves_all_content` | 内容完整性 | 所有关键词（"进程管理"、"内存管理"、"分页"）均出现在分块结果的拼接文本中 | ✅ 通过 |
| 14 | `test_no_empty_chunks_in_result` | 不产生空块 | 含多余空行的文本，返回结果中无空字符串 | ✅ 通过 |
| 15 | `test_three_level_headings_split_correctly` | 多级标题（`#`/`##`/`###`） | 切出至少 3 块 | ✅ 通过 |
| 16 | `test_real_lecture_notes_scenario` | 真实课件结构（标题+正文+列表） | 切出至少 4 个有实质内容的块 | ✅ 通过 |

### 3.3 文本 Hash（`_text_hash`）

| # | 测试名 | 测试目标 | 预期结果 | 实际结果 |
|---|---|---|---|---|
| 17 | `test_same_text_produces_same_hash` | 幂等性 | 同一文本两次调用返回相同 hash | ✅ 通过 |
| 18 | `test_different_text_produces_different_hash` | 区分不同内容 | 不同文本产生不同 hash | ✅ 通过 |
| 19 | `test_hash_is_sha256_format` | 输出格式 | 返回 64 位全小写十六进制字符串 | ✅ 通过 |
| 20 | `test_empty_text_has_stable_hash` | 空字符串稳定性 | 结果与 `hashlib.sha256(b"").hexdigest()` 一致 | ✅ 通过 |
| 21 | `test_whitespace_sensitive` | 空格敏感 | `"abc"` 与 `"abc "` 的 hash 不同 | ✅ 通过 |

### 3.4 综合场景

| # | 测试名 | 测试目标 | 预期结果 | 实际结果 |
|---|---|---|---|---|
| 22 | `test_hash_changes_when_content_changes` | 内容更新触发重建索引 | 修改一个字后 hash 必须变化 | ✅ 通过 |
| 23 | `test_same_content_same_chunks` | 分块幂等性 | 同一文本两次调用返回完全相同的分块列表 | ✅ 通过 |

---

## 4. 向量工具测试（`test_vector_utils.py`）

**被测模块**：`app/db/vector_store.py`

**被测函数**：`_cosine_similarity`、`_rerank`

**背景**：RAG 检索采用两阶段策略——向量库先粗筛 Top-N，再由 `_rerank` 在 Python 侧精确计算余弦相似度重新排序取 Top-K。`_cosine_similarity` 是精排的核心计算单元。

### 4.1 余弦相似度（`_cosine_similarity`）

| # | 测试名 | 测试目标 | 预期结果 | 实际结果 |
|---|---|---|---|---|
| 1 | `test_identical_vectors_have_similarity_one` | 相同向量 | 相似度精确等于 1.0（误差 < 1e-6） | ✅ 通过 |
| 2 | `test_orthogonal_vectors_have_similarity_zero` | 正交向量（如 `[1,0,0]` 与 `[0,1,0]`） | 相似度精确等于 0.0 | ✅ 通过 |
| 3 | `test_opposite_vectors_have_similarity_minus_one` | 反方向向量 | 相似度精确等于 -1.0 | ✅ 通过 |
| 4 | `test_zero_vector_returns_zero` | 零向量（任意方向均无意义） | 两个参数位置均返回 0.0，不抛异常 | ✅ 通过 |
| 5 | `test_known_value` | 已知值验证（45° 夹角） | `(1,1)` 与 `(1,0)` 的相似度 = `1/√2 ≈ 0.7071` | ✅ 通过 |
| 6 | `test_high_dimensional_vectors` | 1536 维向量（与 MiniMax embo-01 相同维度） | 同方向向量相似度接近 1.0（误差 < 1e-4） | ✅ 通过 |
| 7 | `test_symmetry` | 对称性：`sim(a,b) == sim(b,a)` | 两个方向调用的差值 < 1e-10 | ✅ 通过 |

### 4.2 两阶段精排（`_rerank`）

| # | 测试名 | 测试目标 | 预期结果 | 实际结果 |
|---|---|---|---|---|
| 8 | `test_returns_top_k_results` | 返回数量 | 从 4 个候选中返回 `top_k=2` 个结果 | ✅ 通过 |
| 9 | `test_results_sorted_by_score_descending` | 降序排列 | `score` 字段从大到小排列 | ✅ 通过 |
| 10 | `test_most_relevant_is_first` | 最相关排第一 | 与 query 余弦相似度最高的候选块排在 `result[0]` | ✅ 通过 |
| 11 | `test_embedding_field_removed_from_output` | 不泄露内部字段 | 输出结果中不含 `_embedding` 字段 | ✅ 通过 |
| 12 | `test_top_k_larger_than_candidates` | `top_k` 超过候选数量 | 返回全部候选，不越界 | ✅ 通过 |
| 13 | `test_empty_candidates_returns_empty` | 空候选列表 | 返回空列表 | ✅ 通过 |
| 14 | `test_candidates_without_embedding_keep_original_score` | 无 `_embedding` 字段的候选 | 保留原始 score 值，不崩溃；有向量的候选排在前面 | ✅ 通过 |
| 15 | `test_score_precision` | 分数精度 | `score` 字段小数位数 ≤ 4 位（与代码 `round(..., 4)` 对齐） | ✅ 通过 |
| 16 | `test_rerank_changes_initial_order` | 纠正粗筛排序误差 | 即使高相关候选在输入列表末尾，精排后也能排到第一 | ✅ 通过 |

---

## 5. 测试批改测试（`test_quiz_grading.py`）

**被测模块**：`app/services/quiz_service.py`

**被测函数**：`_is_correct`

**背景**：学生提交测试答案后，客观题（单选、多选、判断）由 `_is_correct` 自动批改，结果立即用于计分；简答题走 AI 批改路径。批改准确性直接影响成绩可信度，进而影响学习计划信号质量。

### 5.1 单选题

| # | 测试名 | 测试目标 | 预期结果 | 实际结果 |
|---|---|---|---|---|
| 1 | `test_correct_answer` | 答案正确 | 返回 `True` | ✅ 通过 |
| 2 | `test_wrong_answer` | 答案错误 | 返回 `False` | ✅ 通过 |
| 3 | `test_case_insensitive` | 大小写不敏感 | `"b"` 与 `"B"` 同等正确 | ✅ 通过 |
| 4 | `test_with_whitespace` | 答案含前后空格 | 去空格后正确匹配，返回 `True` | ✅ 通过 |
| 5 | `test_empty_answer` | 学生未作答（空字符串） | 返回 `False` | ✅ 通过 |
| 6 | `test_empty_correct_answer` | 题目无设定正确答案 | 返回 `False` | ✅ 通过 |
| 7 | `test_none_correct_answer` | 正确答案为 `None` | 返回 `False`，不抛异常 | ✅ 通过 |

### 5.2 判断题

| # | 测试名 | 测试目标 | 预期结果 | 实际结果 |
|---|---|---|---|---|
| 8 | `test_true_correct` | 正确答案为 `"true"`，学生答 `"true"` | 返回 `True` | ✅ 通过 |
| 9 | `test_false_correct` | 正确答案为 `"false"`，学生答 `"false"` | 返回 `True` | ✅ 通过 |
| 10 | `test_wrong_true_false` | 答反方向 | 返回 `False` | ✅ 通过 |
| 11 | `test_case_insensitive_true` | `"True"` / `"TRUE"` | 均视为正确 | ✅ 通过 |
| 12 | `test_case_insensitive_false` | `"False"` / `"FALSE"` | 均视为正确 | ✅ 通过 |

### 5.3 多选题

| # | 测试名 | 测试目标 | 预期结果 | 实际结果 |
|---|---|---|---|---|
| 13 | `test_correct_same_order` | 选项顺序相同的正确答案 | 返回 `True` | ✅ 通过 |
| 14 | `test_correct_different_order` | 选项顺序不同但内容相同 | 集合比较，返回 `True` | ✅ 通过 |
| 15 | `test_wrong_missing_option` | 少选（缺少一个正确选项） | 返回 `False` | ✅ 通过 |
| 16 | `test_wrong_extra_option` | 多选（多出一个干扰选项） | 返回 `False` | ✅ 通过 |
| 17 | `test_completely_wrong` | 完全错误的选项组合 | 返回 `False` | ✅ 通过 |
| 18 | `test_single_correct_option` | 只有一个正确选项 | 返回 `True` | ✅ 通过 |
| 19 | `test_comma_separated_fallback` | 正确答案为逗号分隔字符串（非 JSON） | 触发 fallback 解析，返回 `True` | ✅ 通过 |
| 20 | `test_empty_answer_list` | 学生提交空数组 `[]` | 返回 `False` | ✅ 通过 |
| 21 | `test_case_insensitive_multi` | JSON 格式答案精确匹配 | 返回 `True` | ✅ 通过 |

### 5.4 简答题

| # | 测试名 | 测试目标 | 预期结果 | 实际结果 |
|---|---|---|---|---|
| 22 | `test_short_answer_returns_bool` | 调用不崩溃 | 返回 `bool` 类型（简答题实际由 AI 批改，此处只验证不抛异常） | ✅ 通过 |

---

## 6. 智能问答服务测试（`test_chat_service.py`）

**被测模块**：`app/services/chat_service.py`

**被测函数**：`_rag_retrieve`、`send_message`、`save_messages`

**背景**：智能问答是学生最常用的功能，其核心链路为：向量检索（RAG）→ 调用 MiniMax → 响应给前端 → 后台异步写入数据库。测试重点是：检索失败时能否优雅降级；后台写入的数据结构和容错性。

### 6.1 向量检索（`_rag_retrieve`）

| # | 测试名 | 测试目标 | 预期结果 | 实际结果 |
|---|---|---|---|---|
| 1 | `test_returns_results_when_embedding_succeeds` | Embedding 和向量库均正常 | 返回 mock 的检索结果列表 | ✅ 通过 |
| 2 | `test_filters_by_section_id_when_provided` | 指定 `section_id` 时过滤 | 只返回该小节的结果，其他小节结果被丢弃 | ✅ 通过 |
| 3 | `test_returns_empty_when_embedding_fails` | MiniMax Embedding API 抛出异常 | 静默捕获，返回空列表，不向上抛出 | ✅ 通过 |
| 4 | `test_returns_empty_when_vector_store_fails` | 向量库查询抛出异常 | 静默捕获，返回空列表 | ✅ 通过 |
| 5 | `test_returns_empty_list_when_no_results` | 向量库无匹配结果 | 返回空列表 | ✅ 通过 |

### 6.2 主问答流程（`send_message`）

| # | 测试名 | 测试目标 | 预期结果 | 实际结果 |
|---|---|---|---|---|
| 6 | `test_send_message_returns_answer` | 正常调用完整链路 | 返回包含 `answer`、`session_id`、`rag_used`、`suggestions` 的字典 | ✅ 通过 |
| 7 | `test_send_message_includes_save_ctx` | `_save_ctx` 结构完整性 | 返回值中含 `_save_ctx`，且包含 `student_id`、`course_id`、`question`、`answer` 字段 | ✅ 通过 |
| 8 | `test_send_message_rag_used_true_when_refs_exist` | RAG 命中时开关正确 | `rag_used = True`，`references` 非空 | ✅ 通过 |
| 9 | `test_send_message_uses_provided_session_id` | 沿用指定 session | 返回值中的 `session_id` 与入参一致 | ✅ 通过 |
| 10 | `test_send_message_loads_history` | 会话历史传递 | 调用 `answer_question` 时携带了历史消息（第三个参数非空） | ✅ 通过 |
| 11 | `test_send_message_raises_404_if_not_enrolled` | 未加入课程的学生 | 抛出 `HTTPException`（403/404） | ✅ 通过 |

### 6.3 后台异步写入（`save_messages`）

| # | 测试名 | 测试目标 | 预期结果 | 实际结果 |
|---|---|---|---|---|
| 12 | `test_save_messages_writes_two_records` | 写入条数 | 数据库中插入 2 条 `ChatMessage`（user + assistant 各一条） | ✅ 通过 |
| 13 | `test_save_messages_content_correct` | 写入内容正确 | 用户消息内容为原始问题，AI 消息内容为回答，`section_id` 正确传递 | ✅ 通过 |
| 14 | `test_save_messages_handles_db_exception_gracefully` | DB 异常时容错 | 写入失败时调用 `rollback()`，不向外抛出任何异常 | ✅ 通过 |

---

## 7. 个性化学习计划测试（`test_learning_plan_service.py`）

**被测模块**：`app/services/learning_plan_service.py`、`app/services/plan_progress_service.py`

**被测函数**：`_collect_signals`、`_rag_retrieve_for_plan`、`create_plan`、`mark_task`、`get_progress`、`adjust_plan`

**背景**：个性化学习计划是系统最复杂的 AI 功能，依赖对 8 类数据信号的采集、向量检索定位薄弱知识点对应的课程材料、调用 MiniMax 生成计划，以及后续的进度打卡、效果反馈和多轮调整。

### 7.1 信号采集（`_collect_signals`）

| # | 测试名 | 信号类型 | 测试目标 | 预期结果 | 实际结果 |
|---|---|---|---|---|---|
| 1 | `test_empty_student_returns_empty_basis` | 全部 | 无任何数据的新学生 | `basis = {}`，`data_sources = []` | ✅ 通过 |
| 2 | `test_profile_signal_collected` | `profile` | 学生填写了岗位方向和兴趣 | `data_sources` 含 `"profile"`，`basis["profile"]["career_direction"]` 正确 | ✅ 通过 |
| 3 | `test_extra_fields_not_in_profile` | `profile` | `extra` 中包含无关字段（如手机号） | 只采集 `interests` 和 `career_direction`，手机号不出现 | ✅ 通过 |
| 4 | `test_chat_sessions_signal_collected` | `chat_sessions` | 学生有 AI 问答历史 | `data_sources` 含 `"chat_sessions"`，`basis["recent_questions"]` 含问题内容 | ✅ 通过 |
| 5 | `test_questions_signal_collected` | `questions` | 学生向教师提问过 | `data_sources` 含 `"questions"`，`basis["questions_asked"]` 含题目标题 | ✅ 通过 |
| 6 | `test_summaries_signal_collected` | `summaries` | 学生生成过知识点总结 | `data_sources` 含 `"summaries"`，`basis["summaries"]` 含总结标题 | ✅ 通过 |
| 7 | `test_discussions_signal_collected` | `discussions` | 学生在讨论中发表过回复 | `data_sources` 含 `"discussions"`，`basis["discussions_participated"]` 含话题标题 | ✅ 通过 |
| 8 | `test_quiz_records_signal_collected` | `quizzes` | 学生做过测试 | `data_sources` 含 `"quizzes"`，`basis["quiz_records"]` 含测试标题和错题 | ✅ 通过 |
| 9 | `test_data_sources_only_includes_present_signals` | 全部 | 只有 profile 信号时 | `data_sources` 仅含 `"profile"`，不含 `"scores"` / `"chat_sessions"` 等空信号 | ✅ 通过 |

### 7.2 RAG 检索（`_rag_retrieve_for_plan`）

| # | 测试名 | 测试目标 | 预期结果 | 实际结果 |
|---|---|---|---|---|
| 10 | `test_returns_results_for_weak_points` | 有薄弱点时正常检索 | 返回 mock 的相关材料片段 | ✅ 通过 |
| 11 | `test_returns_empty_for_empty_weak_points` | 薄弱点列表为空 | 不调用 Embedding API，直接返回空列表 | ✅ 通过 |
| 12 | `test_returns_empty_on_api_failure` | API 抛出异常 | 静默降级，返回空列表 | ✅ 通过 |
| 13 | `test_weak_points_joined_into_single_query` | 多个薄弱点拼接 | `embed_query` 被调用一次，入参包含所有薄弱点文本 | ✅ 通过 |

### 7.3 计划生成（`create_plan`）

| # | 测试名 | 测试目标 | 预期结果 | 实际结果 |
|---|---|---|---|---|
| 14 | `test_create_plan_returns_plan_fields` | 返回值结构 | 含 `id`、`plan`（2 天）、`analysis`、`data_sources` | ✅ 通过 |
| 15 | `test_create_plan_persisted_to_db` | 持久化 | 数据库中可用 `plan_id` 查到 `LearningPlan` 记录，`student_id`/`course_id` 正确 | ✅ 通过 |
| 16 | `test_create_plan_includes_profile_in_data_sources` | 信号标签 | 有 `career_direction` 的学生，`data_sources` 含 `"profile"` | ✅ 通过 |
| 17 | `test_create_plan_includes_course_materials_when_rag_hits` | RAG 命中 | 向量库有返回时，`data_sources` 含 `"course_materials"` | ✅ 通过 |
| 18 | `test_create_plan_raises_404_when_not_enrolled` | 权限校验 | 未加入课程时抛出 `HTTPException` | ✅ 通过 |

### 7.4 进度打卡（`mark_task` / `get_progress`）

| # | 测试名 | 测试目标 | 预期结果 | 实际结果 |
|---|---|---|---|---|
| 19 | `test_mark_task_creates_progress_record` | 首次打卡 | 创建 `PlanTaskProgress` 记录，`completed=True`，`completed_at` 非空 | ✅ 通过 |
| 20 | `test_mark_task_updates_existing_record` | 重复打卡（同一天） | 更新已有记录，数据库中该天仍只有 1 条记录 | ✅ 通过 |
| 21 | `test_mark_task_invalid_day_raises` | 打卡不存在的天 | 抛出 `HTTPException`（400） | ✅ 通过 |
| 22 | `test_get_progress_returns_all_tasks` | 完成率计算 | `total_days=2`，`completed_days=1`，`completion_rate=0.5` | ✅ 通过 |
| 23 | `test_get_progress_uncompleted_task_has_false` | 未打卡任务的默认值 | `completed=False`，`feedback=null`，`completed_at=null` | ✅ 通过 |

### 7.5 多轮调整（`adjust_plan`）

| # | 测试名 | 测试目标 | 预期结果 | 实际结果 |
|---|---|---|---|---|
| 24 | `test_adjust_archives_old_plan` | 旧计划归档 | 调整后旧计划的 `status` 变为 `"archived"` | ✅ 通过 |
| 25 | `test_adjust_creates_new_plan_with_incremented_version` | 版本链 | 新计划 `version=2`，`parent_plan_id` 等于旧计划 ID | ✅ 通过 |
| 26 | `test_adjust_non_active_plan_raises` | 对归档计划调整 | 抛出 `HTTPException`（400） | ✅ 通过 |

---

## 8. 覆盖范围评估

### 8.1 已覆盖

| 功能模块 | 覆盖层级 | 说明 |
|---|---|---|
| 文本分块策略（段落感知 + 字符降级） | 单元 | 全部分支（空文本、短文本、标题切分、空行切分、超长段落降级）均有用例 |
| 增量索引 hash 比对 | 单元 | hash 幂等性、格式、内容变化检测、空格敏感性 |
| 余弦相似度计算 | 单元 | 特殊值（同向、正交、反向）、高维场景、对称性 |
| 两阶段 Rerank 精排 | 单元 | 排序正确性、字段清除、边界条件（空列表、top_k 超限）、纠正粗筛误差 |
| 客观题自动批改 | 单元 | 单选/多选/判断三类题型，含大小写、空格、JSON 格式、fallback 解析 |
| RAG 检索（问答） | 单元（含 Mock） | 正常路径、section 过滤、两种失败降级 |
| 智能问答主流程 | 单元（含 Mock） | 字段结构、rag_used 开关、历史传递、权限校验 |
| 后台异步消息写入 | 单元（含 Mock） | 写入条数、内容正确性、DB 异常回滚 |
| 8 类信号采集 | 单元（含 Mock） | 每类信号独立测试，验证 data_sources 标签的正确性 |
| RAG 检索（学习计划） | 单元（含 Mock） | 正常路径、空薄弱点跳过、API 失败降级、多薄弱点拼接查询 |
| 计划生成主流程 | 集成（含 Mock） | 返回结构、持久化、data_sources 完整性 |
| 进度打卡与统计 | 集成 | 创建/更新幂等、非法天数报错、completion_rate 计算 |
| 多轮计划调整 | 集成 | 旧计划归档、版本号递增、version chain、对非 active 计划报错 |

### 8.2 未覆盖（已知盲区）

| 模块 | 原因 | 风险 |
|---|---|---|
| HTTP API 层（路由函数） | 需要 `TestClient` 和完整应用上下文，超出当前单元测试范围 | 中：路由参数解析、Auth 中间件行为未验证 |
| MiniMax 真实 API 响应格式 | 需要有效 API Key 和网络访问 | 低：`_parse_json` 有兜底逻辑，格式变化会在运行时快速暴露 |
| pgvector 链路 | 需要 PostgreSQL 实例 | 低：代码路径与 ChromaDB 路径结构相同，核心 Rerank 逻辑已覆盖 |
| C++ 文件处理服务 | 需要编译 pybind11 扩展 | 低：代码中有 `try/except` 降级，功能不依赖它才能运行 |
| 成绩效果反馈（`get_plan_effect`） | 依赖时序数据（计划前后作业提交时间差），构造成本高 | 低：逻辑简单，计算仅涉及日期比较和平均分 |
| 作业提交与 AI 批改流程 | 与本次测试重点不重叠 | 中：作业是主要成绩信号来源，需补充 |

---

## 9. 如何运行测试

```bash
# 进入后端目录
cd backend

# 运行全部测试（详细输出）
uv run pytest tests/ -v

# 只运行某个模块
uv run pytest tests/test_text_chunking.py -v

# 只运行某个测试类
uv run pytest tests/test_learning_plan_service.py::TestCollectSignals -v

# 只运行某个测试函数
uv run pytest tests/test_chat_service.py::TestSendMessage::test_send_message_returns_answer -v

# 显示最慢的 10 个用例（排查耗时）
uv run pytest tests/ --durations=10
```
