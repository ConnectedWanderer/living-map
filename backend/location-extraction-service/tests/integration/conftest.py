import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def small_nlp_models():
    os.environ["SPACY_EN_MODEL"] = "en_core_web_sm"
    os.environ["SPACY_FR_MODEL"] = "fr_core_news_sm"
