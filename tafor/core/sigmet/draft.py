from tafor.core.models import Sigmet
from tafor.core.sigmet.compose import category, composeHeading, validDuration
from tafor.core.sigmet.states import SigmetHeaderState
from tafor.core.utils.time import utcnow


class SigmetDraft:
    """What the editor is drafting: which product, which form, and the header.

    Qt-free. Two pieces of knowledge that used to live in the editor are
    here: the product behind the hazard radios, and the form behind the
    template/cancel/custom radios. The third is the header: the sequence, the
    validity and the area describe the report being written, not the form that
    happens to be on screen, so all six forms share this one object.
    """

    # The form each hazard radio issues, mapped to its designator. Cancel
    # and custom keep whichever product the hazard radios are on -- they
    # are a different axis, not a different product.
    products = {'general': 'WS', 'typhoon': 'WC', 'ash': 'WV', 'airmet': 'WA'}

    def __init__(self, form='general', fir='', airport='',
                 bulletinNumber='', now=utcnow):
        if form not in self.products:
            raise ValueError('Initial form must be a product form: {!r}'.format(form))

        self.form = form
        self.fir = fir
        self.airport = airport
        self.bulletinNumber = bulletinNumber
        self.now = now
        self.header = SigmetHeaderState(designator=self.products[form])
        self.body = None

    @property
    def designator(self):
        return self.header.designator

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
            self.header.designator = self.products[form]
        return True

    def attach(self, body):
        """The body the draft writes: the state behind the form on screen.

        The six bodies stay with their forms; the draft only points at the one
        it is writing, the same way `form` points at the one being shown.
        """
        self.body = body

    def compose(self, locations=None):
        """The message this draft is: heading, body, and nothing else.

        `locations` is the sketch's answer, not the draft's: the canvas owns
        the geometry, so the caller hands its result in.
        """
        heading = composeHeading(self.designator, self.bulletinNumber,
                                 self.airport, self.now())

        if self.hasSketch():
            text = self.body.composeMessage(self.fir, locations or {})
        else:
            text = self.body.composeMessage(self.fir)

        return Sigmet(type=self.designator, heading=heading, text=text)

    def isAcceptable(self):
        """Whether the report could be sent as it stands.

        The canvas is not part of this answer: the draft owns the text, the
        canvas owns the shape, and the editor asks both.
        """
        return bool(self.body) and self.body.isAcceptable()

    def span(self):
        return validDuration(self.designator)

    def category(self):
        return category(self.designator)

    def hasSketch(self):
        """Whether the sketch is part of this draft."""
        return self.form in self.products
