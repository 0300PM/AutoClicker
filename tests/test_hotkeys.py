from types import SimpleNamespace

from hotkeys import HotkeyHook, KeyBinding, key_label, normalise_char, tk_keysym


def pynput_key(**kwargs):
    return SimpleNamespace(**{"name": None, "char": None, "vk": 0, **kwargs})


def tk_event(keysym, char="", keycode=0):
    return SimpleNamespace(keysym=keysym, char=char, keycode=keycode)


def test_binding_from_tk_event_and_back():
    binding = KeyBinding.from_event(tk_event("F8", "", 119))
    assert (binding.label, binding.name, binding.keysym, binding.vk) == ("F8", "f8", "F8", 119)
    restored = KeyBinding.from_dict(binding.as_dict())
    assert restored == binding


def test_binding_matches_pynput_and_tk_events():
    binding = KeyBinding.from_event(tk_event("F8", "", 119))
    assert binding.matches_key(pynput_key(name="f8", vk=119))
    assert binding.matches_event(tk_event("F8", "", 119))
    assert not binding.matches_key(pynput_key(name="f7", vk=118))
    assert not binding.matches_event(tk_event("F7", "", 118))


def test_letter_binding_ignores_case_and_shift():
    binding = KeyBinding.from_event(tk_event("a", "a", 65))
    assert binding.matches_key(pynput_key(char="A", vk=65))
    assert binding.matches_event(tk_event("A", "A", 65))
    assert binding.tk_sequence == "<KeyPress-a>"


def test_symbol_binding_gets_tk_keysym():
    binding = KeyBinding.from_event(tk_event("minus", "-", 189))
    assert binding.char == "-"
    assert binding.keysym == "minus"
    assert binding.tk_sequence == "<KeyPress-minus>"


def test_space_and_enter_labels():
    assert KeyBinding.from_event(tk_event("space", " ", 32)).label == "Spacja"
    assert KeyBinding.from_event(tk_event("Return", "\r", 13)).label == "Enter"
    assert KeyBinding.from_key(pynput_key(name="enter")).label == "Enter"


def test_from_key_produces_matching_binding():
    binding = KeyBinding.from_key(pynput_key(name="scroll_lock", vk=145))
    assert binding.label == "Scroll Lock"
    assert binding.keysym == "Scroll_Lock"
    assert binding.matches_key(pynput_key(name="scroll_lock"))


def test_modifiers_are_rejected():
    for keysym in ("Shift_L", "Control_R", "Alt_L", "Caps_Lock", "Meta_L"):
        assert KeyBinding.from_event(tk_event(keysym, "", 0)).is_modifier
    assert not KeyBinding.from_event(tk_event("F8", "", 119)).is_modifier
    assert not KeyBinding.from_event(tk_event("a", "a", 65)).is_modifier


def test_binding_without_keysym_has_no_tk_sequence():
    binding = KeyBinding(label="?", name="dziwna_nazwa", char=None, vk=None, keysym=None)
    assert binding.tk_sequence is None


def test_empty_or_broken_dict_is_ignored():
    assert KeyBinding.from_dict(None) is None
    assert KeyBinding.from_dict({}) is None
    assert KeyBinding.from_dict({"label": ""}) is None


def test_normalise_char_only_single_characters():
    assert normalise_char("AB") is None
    assert normalise_char("") is None
    assert normalise_char("Ż") == "ż"
    assert normalise_char("7") == "7"


def test_labels_for_function_keys():
    assert key_label("f12", None) == "F12"
    assert key_label(None, "3") == "3"
    assert key_label("media_play", None) == "MEDIA PLAY"


def test_tk_keysym_lookup_prefers_known_names():
    assert tk_keysym("page_up", None) == "Prior"
    assert tk_keysym("f3", None) == "F3"
    assert tk_keysym(None, "q") == "q"
    assert tk_keysym(None, "¬") is None


def test_hotkey_hook_survives_missing_pynput(monkeypatch, capsys):
    def boom(_name):
        raise ImportError("no pynput")

    monkeypatch.setitem(__import__("sys").modules, "pynput", None)
    hook = HotkeyHook(on_press=lambda key: None)
    assert hook.active is False
    assert hook.start() is False
    assert hook.active is False
    hook.stop()
