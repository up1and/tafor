class FormPipeline:
    """Minimal unidirectional state pipeline for form editors.

    Holds raw widget input alongside derived domain state so edits, blurs,
    and external updates flow in one direction without widget-to-widget loops.
    """

    def __init__(
        self,
        initial=None,
        *,
        apply=None,
        rules=None,
        validator=None,
        render=None,
        notify=None,
        changed=None,
        effect=None,
    ):
        self.raw = dict(initial) if initial else {}
        self.previous = dict(self.raw)
        self.apply = apply
        self.rules = rules
        self.validator = validator
        self.render = render
        self.notify = notify
        self.changed = changed
        self.effect = effect

    def value(self, field, default=''):
        """Return the current raw value for ``field``."""
        return self.raw.get(field, default)

    def edit(self, patch, *, source='user', force=False):
        """Apply a partial input patch, derive state, render, and notify."""
        if not patch:
            return False

        changed = {
            key for key, value in patch.items()
            if key not in self.raw or self.raw[key] != value
        }
        if not changed and not force:
            return False

        if force and not changed:
            changed = set(patch.keys())

        self.previous = dict(self.raw)
        self.raw.update(patch)
        self.derive(changed, source)
        self.finish(changed, source)
        return True

    def sync(self, raw, *, source='system', derive=False, changed=False):
        """Replace the raw buffer from an external state snapshot and render."""
        self.previous = dict(raw)
        self.raw = dict(raw)
        if derive:
            self.derive(set(self.raw.keys()), source)
        if self.render:
            self.render()
        if changed and self.changed:
            self.changed()

    def derive(self, changed, source):
        if self.apply:
            self.apply(self.raw)
        if self.rules:
            before = dict(self.raw)
            self.rules(self.raw, self.previous, changed, source)
            if self.apply and self.raw != before:
                self.apply(self.raw)

    def validate(self, scope=None):
        """Run validation for ``scope`` (or the full form when ``None``)."""
        if not self.validator:
            return []

        result = self.validator(scope)
        if not result:
            return []

        patch, errors = result
        patch = patch or {}
        errors = list(errors or ())
        changed = {
            key for key, value in patch.items()
            if key not in self.raw or self.raw[key] != value
        }
        if changed:
            self.previous = dict(self.raw)
            self.raw.update(patch)
            self.derive(changed, 'validate')
            self.finish(changed, 'validate')

        if self.notify:
            for error in errors:
                self.notify(error)

        return errors

    def finish(self, changed, source):
        if self.render:
            self.render()
        if self.changed:
            self.changed()
        if self.effect:
            self.effect(changed, source)
