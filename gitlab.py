import requests
import urllib3
import json
import termcolor
import http.server
import socketserver
from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

parser = argparse.ArgumentParser(description='Blah blah')
parser.add_argument('-token', action="store", dest="token")
parser.add_argument('-username', action="store", dest="user_name")

args = parser.parse_args()

if args.token is None or args.user_name is None:
  exit('You need to specify "-token" and "-username" arguments')

base_url = "https://gitlab.com/api/v4/"

try:
  user_id = requests.get(base_url + "users?username=" + args.user_name, verify=False, headers={'PRIVATE-TOKEN': args.token}).json()[0]['id']
except:
  exit('can not get user_id')

PORT = 6969
url = "https://gitlab.com/api/v4/merge_requests?scope=all&state=opened&approver_ids[]=" + str(user_id)


def getMRsWaitingForMyApproval():
    result = requests.get(url, verify=False, headers={'PRIVATE-TOKEN': args.token})
    try:
        data = result.json()
    except:
        exit('can not get any merge requests' + result)
    mrs_waiting_for_my_approval=list()
    for mr in data:
        if mr['author']['id'] == user_id:
          # This MR was created by you, carry on
          continue
        iid = mr['iid']
        project_id = mr['project_id']
        mr_url = base_url + "projects/" + str(project_id) + "/merge_requests/" + str(iid) + "/approval_state"
        result = requests.get(mr_url, verify=False, headers={'PRIVATE-TOKEN': args.token})
        try:
            mr_approval_state = result.json()
        except:
            exit('can not get approval state for MR: mr=' + mr['iid'])
        waitingForMyApproval = True
        for rule in mr_approval_state['rules']:
            if waitingForMyApproval:
                for approval in rule['approved_by']:
                    if approval['username'] == args.user_name:
                        waitingForMyApproval = False
                        break
        if waitingForMyApproval:
            mrs_waiting_for_my_approval.append(mr)
    return mrs_waiting_for_my_approval

def toHtmlLink(url, description):
    return '<big><a href="' + url + '">' + description + "</a></big></br>"

class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        print("Hitting gitlab's API and processing results...")
        self.send_response(200)
        self.end_headers()
        mrList = getMRsWaitingForMyApproval()
        if len(mrList) == 0:
          outputStr = "<h1>Nothing new for you to review!</h1>"
        else:
          outputStr = ' '.join([toHtmlLink(elem['web_url'], elem['title']) for elem in mrList]) 
        self.wfile.write(str.encode(outputStr))
        print("Done!")

with socketserver.TCPServer(("127.0.0.1", PORT), MyHandler) as httpd:
    print('serving a GET at "http://localhost:%4d"' %(PORT))
    httpd.serve_forever()