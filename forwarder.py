from http.server import BaseHTTPRequestHandler, HTTPServer
import requests, time, re

# https://developers.home-assistant.io/docs/api/rest/

bind_ip = "192.168.2.26"    # Address and port for this server to bind to
bind_port = 8123

hass_ip = "192.168.2.8"     # Address and port of Home Assistant server
hass_port = 8123

# Blacklist/whitelists for commands, domains and entities.
# A '/' after a command indicates the command has parameters.
blacklist_commands = False
command_list = [
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
        headers = _makeHeaders(queries)
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
            self.wfile.write(bytes('Requested endpoint is invalid not allowed', 'utf-8'))

    
    # Handle POST requests    
    def do_POST(self):
        # Parse and filter request
        path, queries = self._parsePath(self.path)
        headers = _makeHeaders(queries)
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
    def _parsePath(path):
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
            key, value = pair.split('=')
            queries[key] = value

        return (pathOnly, queries)

    
    # Takes a URL path and determines if it is a valid and allowable API call.
    # Returns either the input path or None
    def _filterPath(path, POST=False):
        path = path.strip('/')

        # Single command, no parameters
        match = re.fullmatch('api/(\S[^\/]+)')
        if match:
            command = match.groups()[0]
            if _isCommandAllowed(command):
                return path
            else:
                return None

        # Single command, single parameter
        match = re.fullmatch('api/(\S[^\/]+/)(\S[^\/]+)')
        if match:
            command, target = match.groups()
            if _isCommandAllowed(command):
                if command in ['states', 'camera_proxy', 'calendars']:
                    if _isEntityAllowed(target):
                        return path
                    else:
                        return None
                else:
                    return path
            else:
                return None

        # Services
        match = re.fullmatch('api/services/(\S[^\/]+)/(\S[^\/]+)')
        if match and _isCommandAllowed('services/'):
            domain, service = match.groups()
            if _isDomainAllowed(domain) and _isServiceAllowed(service):
                return path
            else:
                return None

        # History
        match = re.fullmatch('api/history/period/(\S[^\/]+)')
        if match and _isCommandAllowed('history/'):
            return path

        # Check config
        if path == 'api/config/core/check_config' and _isCommandAllowed('config/'):
            return path

        # Handle intent
        if path == 'api/intent/handle' and _isCommandAllowed('intent/'):
            return path

        # Blank API call
        if path == 'api':
            return path

        return None

    
    def _isCommandAllowed(command):
        if blacklist_commands ^ (command in command_list):
            return True
        else:
            print(f'Command not allowed: {command}')
            return False

    
    def _isDomainAllowed(domain):
        if blacklist_domains ^ (domain in domain_list):
            return True
        else:
            print(f'Domain not allowed: {domain}')
            return False

    
    def _isEntityAllowed(entity_id):
        if _isDomainAllowed(entity_id.split('.', 1)[0]):
            if blacklist_entities ^ (entity_id in [entity_list]):
                return True
            else:
                print(f'Entity not allowed: {entity_id}')
                return False

    
    # Stub: service filtering not implemented
    def _isServiceAllowed(service):
        return True

    
    # Builds the necessary headers for HA, given the query dict containing the token
    def _makeHeaders(queries):
        if 'token' in queries:
            headers = {'Authorization': 'Bearer '+queries['token'], 'Content-Type': 'application/json'}
            return headers
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
