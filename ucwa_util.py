import requests
import getpass
import json
import uuid
import urllib 
from adal import AuthenticationContext

ucwa_pool_token = {}
ucwa_connection = {}
regional_hostname = ""
ucwa_links = {}

def build_auth_header(token):
    headers = {}
    headers['Authorization'] = "Bearer " + token["accessToken"] 
    headers['Content-Type'] = "application/json"
    return headers

def get_tennantid(domain_name):
    requesturl = "https://login.windows.net/" + domain_name + "/.well-known/openid-configuration"
    tennant_info_response = requests.get(requesturl)
    return tennant_info_response.json()['authorization_endpoint']

def get_accesstoken(resource_url,username,password):
    domain_name = username.split("@")[1]
    auth_endpoint = get_tennantid(domain_name)
    client_id = "d3590ed6-52b3-4102-aeff-aad2292ab01c"
    context = AuthenticationContext(auth_endpoint.replace("/oauth2/authorize",""))
    token_response = context.acquire_token_with_username_password(("https://" + resource_url),username,password,client_id)
    if "accessToken" in token_response:
        return token_response
    else: 
        raise ValueError('Token Could not be retrieved')

def get_regional_endpoint(username,password):
    domain_name = username.split("@")[1]
    defualt_site_url =  'https://webdir.online.lync.com/autodiscover/autodiscoverservice.svc/root?originalDomain=' + domain_name
    region_response = requests.get(defualt_site_url).json()
    if "_links" in region_response:
        if "redirect" in region_response["_links"] :
            region_response = requests.get(region_response["_links"]["redirect"]["href"]).json()
        print("Authing Against " + region_response["_links"]["user"]["href"])
        resource_hostname = urllib.parse.urlparse(region_response["_links"]["user"]["href"]).netloc
        token_reponse = get_accesstoken(resource_hostname,username,password)
        headers =  {"Authorization":"Bearer " + token_reponse["accessToken"]}        
        discover_response = requests.get(region_response["_links"]["user"]["href"],headers=headers)
        return discover_response
    else:
        raise ValueError("Panic")

def connect_ucwa():
    username =  input("Username: ")
    password = getpass.getpass()
    regional_endpoint_response =  get_regional_endpoint(username,password).json()
    global regional_hostname
    regional_hostname = urllib.parse.urlparse(regional_endpoint_response ["_links"]["applications"]["href"]).netloc
    global ucwa_pool_token 
    ucwa_pool_token = get_accesstoken(regional_hostname,username,password)
    headers = build_auth_header(ucwa_pool_token)
    headers['X-MS-RequiresMinResourceVersion'] = "2"
    connect_json_post = {}
    connect_json_post['UserAgent'] = "PhYAgent"
    connect_json_post['Culture'] = "en-US"     
    connect_json_post['EndpointId'] =  str(uuid.uuid4())
    global ucwa_connection
    ucwa_connection = requests.post(regional_endpoint_response["_links"]["applications"]["href"],data=json.dumps(connect_json_post),headers=headers).json()
    make_me_availble()
    global ucwa_links
    headers = build_auth_header(ucwa_pool_token)
    ucwa_link_url =  ("https://" + regional_hostname + ucwa_connection["_embedded"]["me"]["_links"]["self"]["href"])
    ucwa_links = requests.get(ucwa_link_url,headers=headers).json()


def disconnect_ucwa():
    headers = build_auth_header(ucwa_pool_token)
    url = ("https://" + regional_hostname + ucwa_connection["_links"]["self"]["href"])
    return requests.delete(url,headers=headers)
    
def make_me_availble():
    url = ("https://" + regional_hostname + ucwa_connection["_embedded"]["me"]["_links"]["makeMeAvailable"]["href"])
    headers = build_auth_header(ucwa_pool_token)
    make_me_availble_request = {}
    make_me_availble_request['SupportedModalities'] = []
    make_me_availble_request['SupportedModalities'].append("Messaging")
    make_me_availble_request['SupportedMessageFormats'] = []
    make_me_availble_request['SupportedMessageFormats'].append("Plain")
    make_me_availble_request['SupportedMessageFormats'].append("Html")
    return requests.post(url,data=json.dumps(make_me_availble_request),headers=headers)

def send_im():
    message_recipient = input("Message Recipient: ")
    message_subject = input("Message Subject: ")
    message_text = input("Message Text: ")    
    start_messageing_link = ("https://" + regional_hostname + ucwa_connection["_embedded"]["communication"]["_links"]["startMessaging"]["href"])
    headers = build_auth_header(ucwa_pool_token)
    message_json_post = {}
    message_json_post['rel'] = "service:startMessaging"
    message_json_post['subject'] =  message_subject
    message_json_post['operationId'] = str(uuid.uuid4())
    message_json_post['to'] = ("sip:" + message_recipient)
    message_json_post['message'] = ("data:text/plain," + message_text)
    return requests.post(start_messageing_link,data=json.dumps(message_json_post),headers=headers)    

def search_user():
    search_address =  input("address: ")
    headers = build_auth_header(ucwa_pool_token)
    headers['X-MS-RequiresMinResourceVersion'] = "2"
    user_search_url=  ("https://" + regional_hostname + ucwa_links["_links"]["self"]["href"].replace("me","people") + "/search?mail=" + urllib.parse.quote(search_address))
    return requests.get(user_search_url,headers=headers).json()

def get_presence():
    search_address =  input("address: ")
    headers = build_auth_header(ucwa_pool_token)
    headers['X-MS-RequiresMinResourceVersion'] = "2"
    user_search_url=  ("https://" + regional_hostname + ucwa_links["_links"]["self"]["href"].replace("me","people") + "/search?mail=" + urllib.parse.quote(search_address))
    resolved_user = requests.get(user_search_url,headers=headers).json()
    headers = build_auth_header(ucwa_pool_token)
    presence_url =  ("https://" + regional_hostname + resolved_user['_embedded']['contact'][0]['_links']['contactPresence']['href'])
    return requests.get(presence_url,headers=headers).json()








