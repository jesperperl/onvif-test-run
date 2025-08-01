#!/usr/bin/env python3

import hashlib
import os
import base64
from datetime import datetime

username = "tapoperl"
password = "changeme"
# created = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000Z")
created = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z")

raw_nonce = os.urandom(20)
nonce = base64.b64encode(raw_nonce)

sha1 = hashlib.sha1()
sha1.update(raw_nonce + created.encode('utf8') + password.encode('utf8'))
raw_digest = sha1.digest()
digest = base64.b64encode(raw_digest)

template = """<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
    <s:Header>
        <Security s:mustUnderstand="1" xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
            <UsernameToken>
                <Username>{username}</Username>
                <Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{digest}</Password>
                <Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{nonce}</Nonce>
                <Created xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">{created}</Created>
            </UsernameToken>
        </Security>
    </s:Header>
    <s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
        <tds:GetDeviceInformation>
        </tds:GetDeviceInformation>
    </s:Body>
</s:Envelope>"""


# template = """<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">
#     <s:Header>
#         <Security s:mustUnderstand="1" xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
#             <UsernameToken>
#                 <Username>{username}</Username>
#                 <Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest">{digest}</Password>
#                 <Nonce EncodingType="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary">{nonce}</Nonce>
#                 <Created xmlns="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd">{created}</Created>
#             </UsernameToken>
#         </Security>
#     </s:Header>
#     <s:Body xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema">
#         <GetCapabilities xmlns="http://www.onvif.org/ver10/device/wsdl">
#             <Category>All</Category>
#         </GetCapabilities>
#     </s:Body>
# </s:Envelope>"""

req_body = template.format(username=username, nonce=nonce.decode('utf8'), created=created, digest=digest.decode('utf8'))
print(req_body)
