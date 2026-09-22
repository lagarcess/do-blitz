def test_demo_ui_served_at_root(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert b"do-blitz" in response.content
    assert b"/api/v1/data/shorten" in response.content
