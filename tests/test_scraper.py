import pytest

from backend.scraper.scraper import parse_post_element


@pytest.mark.asyncio
async def test_parse_post_element_no_element(monkeypatch):
    class Dummy:
        async def eval_on_selector(self, *_):
            return "title"

        async def get_attribute(self, *_):
            return "/r/test/"

    el = Dummy()
    res = await parse_post_element(el)
    assert isinstance(res, dict)
