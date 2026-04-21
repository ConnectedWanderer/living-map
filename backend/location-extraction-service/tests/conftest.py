import pytest


@pytest.fixture
def sample_english_text():
    return """
    Breaking news from Paris, France. The city of London has announced new climate policies.
    Floods in the Seine river have caused significant damage. Officials from Berlin and Madrid
    are meeting to discuss the response. The United States has also expressed concern about
    global warming effects.
    """


@pytest.fixture
def sample_french_text():
    return """
    Nouvelles de Paris, France. La ville de Londres a annoncé de nouvelles politiques climatiques.
    Les inondations de la Seine ont causé des dommages importants. Des officiels de Berlin et Madrid
    se réunissent pour discuter de la réponse. Les États-Unis ont également exprimé leur préoccupation
    concernant les effets du réchauffement climatique.
    """


@pytest.fixture
def mixed_english_heavy_text():
    return "Bonjour ! Paris is a beautiful city in France. The Seine river flows through London and downtown."


@pytest.fixture
def mixed_french_heavy_text():
    return "Hello ! La ville de Paris est magnifique le week end. La Seine traverse la France et Londres."
