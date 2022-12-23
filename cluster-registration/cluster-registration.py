from flask import Flask, request

from cloudevents.http import from_http

app = Flask(__name__)


# create an endpoint at http://localhost:/8080/
@app.route("/", methods=["POST"])
def home():
    # create a CloudEvent
    event = from_http(request.headers, request.get_data())

    # you can access cloudevent fields as seen below
    print(
        f"Found {event['id']} from {event['source']} with type "
        f"{event['type']} and specversion {event['specversion']}"
    )

    print("AND THE COMPLETE EVENT HAS: %s", event)

    return "", 204

    # List of steps
    # filter by event type (only "add" event is needed)
    # Get the name of the cluster
    # create a manifestwork on the cluster name namespace
    # get the service ip (in a loop) from the manifestwork status
    # query the RF with the cluster name and service IP


if __name__ == "__main__":
    app.run(port=8080)