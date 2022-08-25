from http.server import BaseHTTPRequestHandler, HTTPServer
import requests, time, re

# https://developers.home-assistant.io/docs/api/rest/

bind_ip = "localhost"    # Address and port for this server to bind to
bind_port = 8123

hass_ip = "192.168.2.8"     # Address and port of Home Assistant server
hass_port = 8123

# Long Lived Access Token for Home Assistant.
# Overridden by 'token' key in URL query string.
# Can be left as None if token will be sent in query string.
hass_token = None

# Blacklist/whitelists for actions, domains and entities.
# A '/' after an action indicates the action has parameters.
blacklist_actions = False
action_list = [
'states/',
'services/',
]

blacklist_domains = False
domain_list = [
'light',
'switch',
'group',
]

blacklist_entities = True
entity_list = [
'group.device_trackers',
]

class Forwarder(BaseHTTPRequestHandler):
    # Handle GET requests
    def do_GET(self):
        # Parse and filter request
        path, queries = self._parsePath(self.path)
        headers = self._makeHeaders(queries)
        final_path = self._filterPath(path)

        if final_path is not None:
            # Send request to HA and return HA response to original requester
            requestURL = f'http://{hass_ip}:{hass_port}/{final_path}'
            print(requestURL, headers)
            response = requests.get(requestURL, headers=headers)

            self.send_response(response.status_code)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(bytes(response.text, 'utf-8'))
        else:
            # Return filter error to original sender
            self.send_response(403)
            self.wfile.write(bytes('403: Requested endpoint is invalid or not allowed', 'utf-8'))

    
    # Handle POST requests    
    def do_POST(self):
        # Parse and filter request
        path, queries = self._parsePath(self.path)
        headers = self._makeHeaders(queries)
        final_path = self._filterPath(path)
        dataLength = int(self.headers.get('Content-Length'))
        data = self.rfile.read(dataLength)

        if final_path is not None:
            # Send request to HA and return HA response to original requester
            requestURL = f'http://{hass_ip}:{hass_port}/{final_path}'
            print(requestURL, headers)
            response = requests.post(requestURL, headers=headers, data=data)

            self.send_response(response.status_code)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(bytes(response.text, 'utf-8'))
        else:
            # Return filter error to original sender
            self.send_response(403)
            self.wfile.write(bytes('Requested endpoint is invalid not allowed', 'utf-8'))

    
    # Takes a full URL path with query string and parses it into a path and a dict of queries
    # Example: /this/is/a/path?key=value => ('/this/is/a/path', {'key': 'value'})
    def _parsePath(self, path):
        if '?' in path:
            pathOnly, queryString = path.split('?', 1)
        else:
            pathOnly = path
            queryString = None
        
        if queryString is None:
            queryPairs = []
        elif '&' in queryString:
            queryPairs = queryString.split('&')
        else:
            queryPairs = [queryString]
        
        queries = {}
        for pair in queryPairs:
            if '=' in pair:
                key, value = pair.split('=')
                queries[key] = value

        return (pathOnly, queries)

    
    # Takes a URL path and determines if it is a valid and allowable API call.
    # Returns either the input path or None
    def _filterPath(self, path):
        path = path.strip('/')

        # Single action, no parameters
        match = re.fullmatch('api/(\S[^\/]+)', path)
        if match:
            action = match.groups()[0]
            if self._isActionAllowed(action):
                return path
            else:
                return None

        # Single action, single parameter
        match = re.fullmatch('api/(\S[^\/]+/)(\S[^\/]+)', path)
        if match:
            action, target = match.groups()
            if self._isActionAllowed(action):
                if action in ['states/', 'camera_proxy/', 'calendars/']:
                    if self._isEntityAllowed(target):
                        return path
                    else:
                        return None
                else:
                    return path
            else:
                return None

        # Services
        match = re.fullmatch('api/services/(\S[^\/]+)/(\S[^\/]+)', path)
        if match and self._isActionAllowed('services/'):
            domain, service = match.groups()
            if self._isDomainAllowed(domain) and self._isServiceAllowed(service):
                return path
            else:
                return None

        # History
        match = re.fullmatch('api/history/period/(\S[^\/]+)', path)
        if match and self._isActionAllowed('history/'):
            return path

        # Check config
        if path == 'api/config/core/check_config' and self._isActionAllowed('config/'):
            return path

        # Handle intent
        if path == 'api/intent/handle' and self._isActionAllowed('intent/'):
            return path

        # Blank API call
        if path == 'api':
            return 'api/'

        return None

    
    def _isActionAllowed(self, action):
        if blacklist_actions ^ (action in action_list):
            return True
        else:
            print(f'Action not allowed: {action}')
            return False

    
    def _isDomainAllowed(self, domain):
        if blacklist_domains ^ (domain in domain_list):
            return True
        else:
            print(f'Domain not allowed: {domain}')
            return False

    
    def _isEntityAllowed(self, entity_id):
        if self._isDomainAllowed(entity_id.split('.', 1)[0]):
            if blacklist_entities ^ (entity_id in entity_list):
                return True
            else:
                print(f'Entity not allowed: {entity_id}')
                return False

    
    # Stub: service filtering not implemented
    def _isServiceAllowed(self, service):
        return True

    
    # Builds the necessary headers for HA, given the query dict containing the token
    def _makeHeaders(self, queries):
        if 'token' in queries:
            token = queries['token']
        else:
            token = hass_token
        
        if token is not None:
            return {'Authorization': 'Bearer '+token, 'Content-Type': 'application/json'}
        else:
            return None


if __name__ == "__main__":        
    forwarder = HTTPServer((bind_ip, bind_port), Forwarder)
    print("Server started at http://%s:%s" % (bind_ip, bind_port))

    try:
        forwarder.serve_forever()
    except KeyboardInterrupt:
        pass

    forwarder.server_close()
    print("Server stopped.")
