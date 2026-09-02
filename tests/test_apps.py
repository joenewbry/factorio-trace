from factorio_trace.apps import is_factorio_app


def test_factorio_process_name():
    assert is_factorio_app(name="Factorio")
    assert is_factorio_app(name="factorio")
    assert is_factorio_app(exe="C:/Games/factorio.exe")
    assert is_factorio_app(bundle_id="com.factorio")


def test_does_not_match_this_repo_or_a_browser_tab_title_alone():
    assert not is_factorio_app(name="factorio-trace")
    assert not is_factorio_app(name="Code", window_title="factorio-trace")
    assert not is_factorio_app(name="Google Chrome", window_title="Factorio")
    assert not is_factorio_app(name="Safari", exe="/Applications/Safari.app/Contents/MacOS/Safari")
