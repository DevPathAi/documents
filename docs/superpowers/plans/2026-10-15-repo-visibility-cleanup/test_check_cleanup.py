import hashlib
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_cleanup as cc  # noqa: E402


class MdLinksTest(unittest.TestCase):
    def test_target_with_parentheses_is_read_whole(self):
        text = "| [노트](./📓-Knowledge-Notes-모듈-상세-설계-(v5.0).md) | M8 |"
        self.assertEqual(cc.md_links(text), [(1, "./📓-Knowledge-Notes-모듈-상세-설계-(v5.0).md", "md")])

    def test_image_is_skipped(self):
        self.assertEqual(cc.md_links("![그림](./img/a.png) [문서](./b.md)"), [(1, "./b.md", "md")])

    def test_title_after_space_is_dropped(self):
        self.assertEqual(cc.md_links('[a](./b.md "제목")'), [(1, "./b.md", "md")])

    def test_wiki_link_with_alias_and_anchor(self):
        self.assertEqual(cc.md_links("| 28 | [[28_장기_전략#요약|장기 전략]] |"), [(1, "28_장기_전략", "wiki")])

    def test_two_links_on_one_line(self):
        text = "[29](./29_a.md) · [35](./35_b.md)."
        self.assertEqual([t for _, t, _ in cc.md_links(text)], ["./29_a.md", "./35_b.md"])


class HashedNameTest(unittest.TestCase):
    SHA = {hashlib.sha256("홍길동".encode("utf-8")).hexdigest()}

    def test_finds_name_inside_longer_run(self):
        self.assertEqual(cc.hashed_name_hits("멘토: 홍길동대표(회사)", self.SHA), 1)

    def test_no_hit(self):
        self.assertEqual(cc.hashed_name_hits("멘토 배정 확정", self.SHA), 0)


class DisplayWidthTest(unittest.TestCase):
    def test_hangul_is_double_width(self):
        self.assertEqual(cc.display_width("│가a│"), 5)


class LinkResolvesTest(unittest.TestCase):
    EXISTS = staticmethod(lambda rel: cc._norm(rel) in {"a.md", "docs/b.md", "28_장기_전략.md"})

    def test_external_and_anchor_links_are_ok(self):
        for t in ("https://x.y", "#anchor", "mailto:a@b", "/abs"):
            self.assertTrue(cc.link_resolves(self.EXISTS, t, "md"))

    def test_relative_and_encoded_paths(self):
        self.assertTrue(cc.link_resolves(self.EXISTS, "./docs/b.md#sec", "md"))
        self.assertTrue(cc.link_resolves(self.EXISTS, "./28_%EC%9E%A5%EA%B8%B0_%EC%A0%84%EB%9E%B5.md", "md"))
        self.assertFalse(cc.link_resolves(self.EXISTS, "./missing.md", "md"))

    def test_wiki_link_resolves_to_md(self):
        self.assertTrue(cc.link_resolves(self.EXISTS, "28_장기_전략", "wiki"))
        self.assertFalse(cc.link_resolves(self.EXISTS, "29_없음", "wiki"))


class MovedLinksTest(unittest.TestCase):
    def test_md_and_wiki_links_to_moved_files_are_found(self):
        docs = {"R.md": "| 28 | [장기](./28_장기_전략.md) |\n| 29 | [[29_예비창업패키지_사업계획서]] |\n[ok](./a.md)"}
        self.assertEqual(cc.links_to_moved(docs.__getitem__, ["R.md"]),
                         ["R.md:1->./28_장기_전략.md", "R.md:2->29_예비창업패키지_사업계획서"])

    def test_new_broken_is_difference_from_base(self):
        base = {"R.md": "[[Note Title]] [a](./a.md)"}
        now = {"R.md": "[[Note Title]] [a](./a.md) [x](./28_장기_전략.md)"}
        before = cc.broken_links(base.__getitem__, lambda r: cc._norm(r) in {"a.md", "28_장기_전략.md"}, ["R.md"])
        after = cc.broken_links(now.__getitem__, lambda r: cc._norm(r) in {"a.md"}, ["R.md"])
        self.assertEqual(after - before, {("R.md", "./28_장기_전략.md", "md")})


if __name__ == "__main__":
    unittest.main()
