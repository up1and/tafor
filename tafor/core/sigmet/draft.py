from tafor.core.sigmet.compose import category, validDuration


class SigmetDraft:
    """What the editor is drafting: which product, and which form.

    Qt-free. Two pieces of knowledge that used to live in the editor are
    here: the product behind the hazard radios, and the form behind the
    template/cancel/custom radios.
    """

    # The form each hazard radio issues, mapped to its designator. Cancel
    # and custom keep whichever product the hazard radios are on -- they
    # are a different axis, not a different product.
    products = {'general': 'WS', 'typhoon': 'WC', 'ash': 'WV', 'airmet': 'WA'}

    def __init__(self, designator='WS', form='general'):
        self.designator = designator
        self.form = form

    def select(self, form):
        """Switch to form; returns whether anything changed.

        Radio clicks fire even on the already-checked radio, and the
        caller's rendering resets the span and clears the sketch, so the
        caller renders only when this returns True.
        """
        if form == self.form:
            return False

        self.form = form
        if form in self.products:
            self.designator = self.products[form]
        return True

    def span(self):
        return validDuration(self.designator)

    def category(self):
        return category(self.designator)

    def hasSketch(self):
        """Whether the sketch is part of this draft."""
        return self.form in self.products
