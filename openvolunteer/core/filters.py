EXPECTED_TUPLE_LEN = 2


def normalize_choices(choices):
    """
    Ensure choices are always [(value, label), ...]
    """
    normalized = []

    for item in choices:
        # Already a tuple (value, label)
        if isinstance(item, (tuple, list)) and len(item) == EXPECTED_TUPLE_LEN:
            normalized.append(item)

        # Model instance
        elif hasattr(item, "id"):
            normalized.append((str(item.id), str(item)))

        else:
            msg = f"Invalid choice item: {item!r}. "
            raise ValueError(
                msg,
                "Choices must be (value, label) or model instances.",
            )

    return normalized


def apply_filters(request, queryset, filter_defs):
    filters_ctx = []

    for f in filter_defs:
        value = request.GET.get(f["name"])

        choices = f.get("choices")
        if callable(choices):
            choices = choices(request)

        if choices is not None:
            choices = normalize_choices(choices)

        ctx = {
            "name": f["name"],
            "label": f.get("label", f["name"].title()),
            "type": f["type"],
            "choices": choices,
            "value": value,
        }
        filters_ctx.append(ctx)

        if value in ("", None):
            continue

        if f["type"] == "boolean":
            value = value == "1"

        if "filter" in f:
            queryset = f["filter"](queryset, request, value)
            continue

        lookup = f.get("lookup")
        if lookup:
            queryset = queryset.filter(**{lookup: value})

    return queryset.distinct(), {
        "filters": filters_ctx,
        "filters_active": any(f["value"] for f in filters_ctx),
    }
