import math


class Pagination(object):

    def __init__(self, paginate, page, perPage, total, items):
        self.paginate = paginate
        self.page = page
        self.perPage = perPage
        self.total = total
        self.items = items

    @property
    def pages(self):
        """The total number of pages"""
        if self.perPage == 0:
            pages = 0
        else:
            pages = int(math.ceil(self.total / float(self.perPage)))
        return pages

    def prev(self):
        """Returns a :class:`Pagination` object for the previous page."""
        assert self.paginate is not None, 'a paginate function is required '
        return self.paginate(self.page - 1, self.perPage)

    @property
    def prevNum(self):
        """Number of the previous page."""
        if not self.hasPrev:
            return None
        return self.page - 1

    @property
    def hasPrev(self):
        """True if a previous page exists"""
        return self.page > 1

    def next(self):
        """Returns a :class:`Pagination` object for the next page."""
        assert self.paginate is not None, 'a paginate function is required '
        return self.paginate(self.page + 1, self.perPage)

    @property
    def hasNext(self):
        """True if a next page exists."""
        return self.page < self.pages

    @property
    def nextNum(self):
        """Number of the next page"""
        if not self.hasNext:
            return None
        return self.page + 1


def paginate(queryset, page=None, perPage=None):
    if page is None or page < 1:
        page = 1

    if perPage is None or perPage < 0:
        perPage = 20

    items = queryset.limit(perPage).offset((page - 1) * perPage).all()

    if page == 1 and len(items) < perPage:
        total = len(items)
    else:
        total = queryset.order_by(None).count()

    return Pagination(paginate, page, perPage, total, items)



