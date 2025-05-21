def test_webhook(mock_feed):
    from feedscoring.main import post_webhook

    assert post_webhook().status_code == 200
    assert post_webhook().headers["x-custom-header"] == "secret"
