"""
向量工具函数测试。

测试目标：
  - _cosine_similarity：余弦相似度计算
  - _rerank：两阶段 Rerank 精排
"""
import math

import pytest

from app.db.vector_store import _cosine_similarity, _rerank


# ─────────────────────────────────────────────────────────────
# _cosine_similarity 测试
# ─────────────────────────────────────────────────────────────

class TestCosineSimilarity:
    def test_identical_vectors_have_similarity_one(self):
        v = [1.0, 2.0, 3.0]
        result = _cosine_similarity(v, v)
        assert abs(result - 1.0) < 1e-6

    def test_orthogonal_vectors_have_similarity_zero(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        result = _cosine_similarity(a, b)
        assert abs(result) < 1e-6

    def test_opposite_vectors_have_similarity_minus_one(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        result = _cosine_similarity(a, b)
        assert abs(result - (-1.0)) < 1e-6

    def test_zero_vector_returns_zero(self):
        zero = [0.0, 0.0, 0.0]
        v = [1.0, 2.0, 3.0]
        assert _cosine_similarity(zero, v) == 0.0
        assert _cosine_similarity(v, zero) == 0.0

    def test_known_value(self):
        # a=(1,1), b=(1,0)：cos(45°) = 1/√2 ≈ 0.7071
        a = [1.0, 1.0]
        b = [1.0, 0.0]
        result = _cosine_similarity(a, b)
        assert abs(result - 1 / math.sqrt(2)) < 1e-6

    def test_high_dimensional_vectors(self):
        """1536 维向量（与 MiniMax embo-01 维度相同）正常工作。"""
        dim = 1536
        a = [0.1] * dim
        b = [0.2] * dim
        result = _cosine_similarity(a, b)
        # 同方向向量，相似度应为 1.0
        assert abs(result - 1.0) < 1e-4

    def test_symmetry(self):
        """余弦相似度应满足对称性：sim(a,b) == sim(b,a)。"""
        a = [1.0, 2.0, 3.0, 4.0]
        b = [0.5, 1.5, 2.5, 3.5]
        assert abs(_cosine_similarity(a, b) - _cosine_similarity(b, a)) < 1e-10


# ─────────────────────────────────────────────────────────────
# _rerank 测试
# ─────────────────────────────────────────────────────────────

def _make_candidate(text: str, section_id: str, embedding: list[float]) -> dict:
    """构造一个带 _embedding 的候选块字典。"""
    return {
        "section_id": section_id,
        "section_title": f"小节 {section_id}",
        "file_name": "test.pdf",
        "excerpt": text,
        "score": 0.0,  # 精排前分数，将被覆盖
        "_embedding": embedding,
    }


class TestRerank:
    def test_returns_top_k_results(self):
        query = [1.0, 0.0, 0.0]
        candidates = [
            _make_candidate("块 A", "s1", [1.0, 0.0, 0.0]),   # 相似度 1.0
            _make_candidate("块 B", "s2", [0.0, 1.0, 0.0]),   # 相似度 0.0
            _make_candidate("块 C", "s3", [0.7, 0.7, 0.0]),   # 相似度 ~0.707
            _make_candidate("块 D", "s4", [0.5, 0.5, 0.7]),   # 相似度 ~0.408
        ]
        result = _rerank(candidates, query, top_k=2)
        assert len(result) == 2

    def test_results_sorted_by_score_descending(self):
        """返回结果应按余弦相似度从高到低排序。"""
        query = [1.0, 0.0]
        candidates = [
            _make_candidate("低相关", "s_low", [0.0, 1.0]),    # 相似度 0.0
            _make_candidate("高相关", "s_high", [1.0, 0.0]),   # 相似度 1.0
            _make_candidate("中相关", "s_mid", [0.7, 0.7]),    # 相似度 ~0.707
        ]
        result = _rerank(candidates, query, top_k=3)
        scores = [r["score"] for r in result]
        assert scores == sorted(scores, reverse=True), "结果应按相似度降序排列"

    def test_most_relevant_is_first(self):
        """与 query 最相似的候选块应排在第一位。"""
        query = [1.0, 0.0, 0.0]
        candidates = [
            _make_candidate("无关内容", "s_irrelevant", [0.0, 0.0, 1.0]),
            _make_candidate("最相关内容", "s_best", [1.0, 0.0, 0.0]),
            _make_candidate("一般内容", "s_mid", [0.5, 0.5, 0.0]),
        ]
        result = _rerank(candidates, query, top_k=3)
        assert result[0]["section_id"] == "s_best"

    def test_embedding_field_removed_from_output(self):
        """精排后 _embedding 内部字段不应出现在返回结果中。"""
        query = [1.0, 0.0]
        candidates = [_make_candidate("内容", "s1", [1.0, 0.0])]
        result = _rerank(candidates, query, top_k=1)
        assert "_embedding" not in result[0], "_embedding 不应出现在输出中"

    def test_top_k_larger_than_candidates(self):
        """当 top_k 大于候选数量时，应返回全部候选。"""
        query = [1.0, 0.0]
        candidates = [_make_candidate("内容", "s1", [1.0, 0.0])]
        result = _rerank(candidates, query, top_k=10)
        assert len(result) == 1

    def test_empty_candidates_returns_empty(self):
        result = _rerank([], [1.0, 0.0, 0.0], top_k=3)
        assert result == []

    def test_candidates_without_embedding_keep_original_score(self):
        """
        没有 _embedding 字段的候选块不会崩溃，
        保留原始 score 值（0.0），会被排到末尾。
        """
        query = [1.0, 0.0]
        candidates = [
            {"section_id": "s1", "excerpt": "有向量", "score": 0.0,
             "_embedding": [1.0, 0.0]},
            {"section_id": "s2", "excerpt": "无向量", "score": 0.5},  # 无 _embedding
        ]
        result = _rerank(candidates, query, top_k=2)
        assert len(result) == 2
        # 有向量的那个相似度为 1.0，应排第一
        assert result[0]["section_id"] == "s1"

    def test_score_precision(self):
        """score 应保留 4 位小数（与代码中 round(..., 4) 一致）。"""
        query = [1.0, 1.0]
        candidates = [_make_candidate("内容", "s1", [1.0, 0.0])]
        result = _rerank(candidates, query, top_k=1)
        score = result[0]["score"]
        # 将 score 转为字符串检验小数位数
        decimal_places = len(str(score).split(".")[-1]) if "." in str(score) else 0
        assert decimal_places <= 4

    def test_rerank_changes_initial_order(self):
        """
        精排应能纠正向量库粗筛的排序误差：
        即使候选列表按"低相似度在前"给出，精排后也应让高相似度排第一。
        """
        query = [1.0, 0.0]
        # 故意将高相关放在列表末尾，模拟粗筛排序不准确
        candidates = [
            _make_candidate("低相关（粗筛排第一）", "s_low", [0.1, 0.99]),
            _make_candidate("中相关", "s_mid", [0.5, 0.5]),
            _make_candidate("高相关（粗筛排最后）", "s_high", [0.99, 0.1]),
        ]
        result = _rerank(candidates, query, top_k=1)
        assert result[0]["section_id"] == "s_high", "精排应把最相关的排到第一位"
