"""Finding records again: keyword, status category, date range, usage level."""


def filter_records(records, keyword=None, status=None, start=None, end=None, min_per_person=None):
    """Return records matching ALL of the filters that were given.

    Dates are ISO strings, which sort correctly as plain text.
    """
    found = []
    word = keyword.lower().strip() if keyword else None
    for rec in records:
        if word:
            haystack = f"{rec.date} {rec.notes} {rec.status}".lower()
            if word not in haystack:
                continue
        if status and rec.status.lower() != status.lower():
            continue
        if start and rec.date < start:
            continue
        if end and rec.date > end:
            continue
        if min_per_person is not None and rec.per_person_liters < min_per_person:
            continue
        found.append(rec)
    return sorted(found, key=lambda r: (r.date, r.record_id))
