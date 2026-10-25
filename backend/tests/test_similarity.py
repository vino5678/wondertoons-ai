from app.providers.similarity import TextOverlapSimilarityChecker


def test_identical_text_scores_high_and_never_claims_visual_uniqueness():
    c = TextOverlapSimilarityChecker()
    m = c.compare({"name": "Fox", "appearance": "orange fox with big eyes"},
                  [{"id": "a", "name": "Fox", "appearance": "orange fox with big eyes"},
                   {"id": "b", "name": "Owl", "appearance": "grey owl"}])
    assert m[0].character_id == "a" and m[0].score == 1.0 and m[1].score < 0.5
    assert c.guarantees_visual_uniqueness is False


def test_tamil_tokens_not_split():
    c = TextOverlapSimilarityChecker()
    m = c.compare({"name": "நரி", "appearance": "ஆரஞ்சு நரி"}, [{"id": "a", "name": "நரி", "appearance": "ஆரஞ்சு நரி"}])
    assert m[0].score == 1.0
