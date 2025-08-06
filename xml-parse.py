import xml.etree.ElementTree as ET

if __name__ == "__main__":
    print("Parsing XML...")
    xml_text = """<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://www.w3.org/2003/05/soap-envelope" xmlns:tds="http://www.onvif.org/ver10/device/wsdl">
    <SOAP-ENV:Header>
    </SOAP-ENV:Header>
    <SOAP-ENV:Body>
        <tds:GetSystemDateAndTime/>
    </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
"""
    print(xml_text)
    try:
        root = ET.fromstring(xml_text)
        print(root)

        action = {'action': None, 'namespace': '', 'element': None}

        # Find the action in the body
        body = root.find('.//{http://www.w3.org/2003/05/soap-envelope}Body')
        if body is not None:
            for child in body:
                action = {
                    'action': child.tag.split('}')[-1] if '}' in child.tag else child.tag,
                    'namespace': child.tag.split('}')[0][1:] if '}' in child.tag else '',
                    'element': child
                }

        print(action)
    except ET.ParseError:
        print(ET)
        print(ET.ParseError)
        pass
