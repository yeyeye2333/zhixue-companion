"""
文本分块函数测试。

测试目标：
  - _char_split：超长文本字符级分块
  - _split_text：段落/标题感知分块（主策略）
  - _text_hash：SHA-256 摘要一致性
"""
import hashlib

import pytest

from app.services.section_service import _CHUNK_SIZE, _char_split, _split_text, _text_hash


# ─────────────────────────────────────────────────────────────
# _char_split 测试
# ─────────────────────────────────────────────────────────────

class TestCharSplit:
    def test_empty_text_returns_empty(self):
        assert _char_split("") == []

    def test_short_text_returns_single_chunk(self):
        text = "这是一段很短的文本，不超过分块大小。"
        result = _char_split(text)
        assert len(result) == 1
        assert result[0] == text.strip()

    def test_long_text_splits_into_multiple_chunks(self):
        # 构造一段明显超过 _CHUNK_SIZE 的文本
        text = "A" * (_CHUNK_SIZE * 3)
        result = _char_split(text)
        assert len(result) > 1, "超长文本应被分成多个块"

    def test_all_chunks_within_max_size(self):
        # 每个块不应超过 _CHUNK_SIZE 的 1.5 倍（允许在句子边界略微超出）
        text = "这是一个句子。" * 200
        for chunk in _char_split(text):
            assert len(chunk) <= _CHUNK_SIZE * 1.5, f"块长度 {len(chunk)} 超出限制"

    def test_splits_at_sentence_boundary(self):
        # 句号附近优先断开
        sentence = "这是第一句话。" * 40 + "这是第二句话。" * 40
        chunks = _char_split(sentence)
        # 大多数块应在中文句号处结尾，而非中间截断
        ends_with_period = sum(1 for c in chunks if c.endswith("。") or c.endswith("."))
        assert ends_with_period >= len(chunks) * 0.5, "应有超过一半的块在句号处结束"

    def test_no_empty_chunks(self):
        text = "内容\n\n\n" * 100
        for chunk in _char_split(text):
            assert chunk.strip() != "", "不应返回空块"


# ─────────────────────────────────────────────────────────────
# _split_text 测试
# ─────────────────────────────────────────────────────────────

class TestSplitText:
    def test_empty_text_returns_empty(self):
        assert _split_text("") == []

    def test_short_text_kept_as_single_chunk(self):
        text = "这是一小段内容，没有空行也没有标题。"
        result = _split_text(text)
        assert len(result) == 1
        assert result[0] == text

    def test_splits_on_blank_lines(self):
        """两个段落之间有空行，应切分为两块。"""
        text = "第一段内容，讲述概念 A。\n\n第二段内容，讲述概念 B。"
        result = _split_text(text)
        assert len(result) == 2
        assert "第一段" in result[0]
        assert "第二段" in result[1]

    def test_splits_on_markdown_headings(self):
        """Markdown 标题应作为新段落的切分点。"""
        text = "引言段落，介绍背景。\n## 第一节：基础知识\n基础知识的内容。\n## 第二节：进阶\n进阶内容。"
        result = _split_text(text)
        # 至少应切出 3 段（引言、第一节、第二节）
        assert len(result) >= 3, f"应至少有 3 块，实际得到 {len(result)} 块：{result}"
        # 标题行应出现在某个块的开头
        has_heading = any(c.startswith("##") or "\n##" in c or c.strip().startswith("##")
                          for c in result)
        assert has_heading, "标题内容应保留在分块中"

    def test_multiple_blank_lines_treated_as_one_separator(self):
        """多个连续空行应等同于单个段落分隔。"""
        text = "段落一。\n\n\n\n段落二。"
        result = _split_text(text)
        assert len(result) == 2

    def test_long_paragraph_gets_further_split(self):
        """超过 _CHUNK_SIZE 的单段落应被进一步字符分块。"""
        # 一个超长段落，没有空行
        long_para = "这是很长的一句话内容。" * 100  # ~1100 字
        assert len(long_para) > _CHUNK_SIZE
        result = _split_text(long_para)
        assert len(result) > 1, "超长单段落应被进一步分块"

    def test_preserves_all_content(self):
        """所有原始文字内容应在分块结果中有所体现，不会丢弃。"""
        text = "## 第一章\n\n进程管理是操作系统的核心。\n\n## 第二章\n\n内存管理涉及分页和分段。"
        result = _split_text(text)
        joined = " ".join(result)
        assert "进程管理" in joined
        assert "内存管理" in joined
        assert "分页" in joined

    def test_no_empty_chunks_in_result(self):
        """返回列表中不应含有空字符串或纯空白块。"""
        text = "\n\n\n## 标题\n\n内容\n\n\n另一段\n\n"
        for chunk in _split_text(text):
            assert chunk.strip() != "", "不应返回空块"

    def test_three_level_headings_split_correctly(self):
        """多级标题（# / ## / ###）均应作为切分点。"""
        text = (
            "# 第一章\n概述。\n\n"
            "## 1.1 节\n节内容。\n\n"
            "### 1.1.1 子节\n子节内容。"
        )
        result = _split_text(text)
        assert len(result) >= 3

    def test_real_lecture_notes_scenario(self):
        """模拟真实课件文本：含标题、段落、列表。"""
        text = """## 进程状态转换

进程在生命周期内会经历多种状态。

常见的三种基本状态：
- 就绪（Ready）：等待 CPU
- 运行（Running）：占用 CPU 执行
- 阻塞（Blocked）：等待 I/O 等事件

## 调度算法

### FCFS（先来先服务）

最简单的调度算法，按照进程到达顺序分配 CPU。

优点：实现简单，公平性好。
缺点：平均等待时间可能较长，不适合交互式系统。

### SJF（最短作业优先）

优先调度预计执行时间最短的进程。"""
        result = _split_text(text)
        # 应切出多个有意义的块
        assert len(result) >= 4, f"真实课件文本应切出至少 4 块，实际 {len(result)} 块"
        # 每块都有实质内容
        for chunk in result:
            assert len(chunk.strip()) > 0


# ─────────────────────────────────────────────────────────────
# _text_hash 测试
# ─────────────────────────────────────────────────────────────

class TestTextHash:
    def test_same_text_produces_same_hash(self):
        text = "进程管理是操作系统的核心内容。"
        assert _text_hash(text) == _text_hash(text)

    def test_different_text_produces_different_hash(self):
        assert _text_hash("文本 A") != _text_hash("文本 B")

    def test_hash_is_sha256_format(self):
        h = _text_hash("任意内容")
        # SHA-256 十六进制表示应为 64 个字符
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_empty_text_has_stable_hash(self):
        expected = hashlib.sha256(b"").hexdigest()
        assert _text_hash("") == expected

    def test_whitespace_sensitive(self):
        """前后空白不同的文本 hash 应不同（精确比对）。"""
        assert _text_hash("abc") != _text_hash("abc ")


# ─────────────────────────────────────────────────────────────
# 综合场景：分块后 hash 变化检测
# ─────────────────────────────────────────────────────────────

class TestChunkingWithHash:
    def test_hash_changes_when_content_changes(self):
        """内容修改后 hash 必须变化，以触发增量重建索引。"""
        v1 = "## 第一章\n\n进程管理概述。"
        v2 = "## 第一章\n\n进程管理概述（已更新内容）。"
        assert _text_hash(v1) != _text_hash(v2)

    def test_same_content_same_chunks(self):
        """相同内容两次分块结果应完全一致（幂等性）。"""
        text = "## 标题\n\n段落一。\n\n段落二，内容更长一些。"
        assert _split_text(text) == _split_text(text)
