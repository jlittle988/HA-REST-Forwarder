# HA-REST-Forwarder
A simple HTTP server that forwards REST API requests to a Home Assistant server. The Home Assistant authentication token can passed in the URL, for rare applications where header access is not available. Requests can be filtered (whitelisted or blacklisted) by command, domain and entity for improved security.

## Usage
### Authentication
Requests follow the same format as the [Home Assistant REST API](https://developers.home-assistant.io/docs/api/rest/). To include the authentication token in the request, specify it with the `token` keyword as shown below:

`http://localhost:8123/api/?token=ABCDEF...`

To include the authentication token in the script, set it with `hass_token`. This variable is only used if the `token` keyword is not included in the URL.

### Filtering
The available API endpoints can be restricted with `action_list`, `domain_list` and `entity_list`, to prevent access to sensitive data. Note that `states` and `states/` are different - the forward slash indicates that the action has parameters. `states` is the action to request the state of every entity, so it is recommended that this is filtered out.