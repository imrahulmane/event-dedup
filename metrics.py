
from prometheus_client import Counter, Histogram
from prometheus_client.asgi import make_asgi_app

metrics_app = make_asgi_app()

events_received_total = Counter(
    "events_received_total",
    "Total Number of events received by the API"
)

accepted_events_total = Counter(
    "events_accepted_total",
    "Total Number of events accepted by the API"
)

duplicate_events_received_total = Counter(
    "duplicate_events_received_total",
    "Total Number of duplicate events received by the API"
)

event_processing_seconds = Histogram(
    "event_processing_seconds",
    "Time spent processing an event request"
)