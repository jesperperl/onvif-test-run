from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import uuid
import base64
import hashlib
import secrets
from typing import Optional, Dict, Any
import uvicorn

app = FastAPI(title="ONVIF Service Server", version="1.0.0")

# ONVIF namespace definitions
NAMESPACES = {
    'soap': 'http://www.w3.org/2003/05/soap-envelope',
    'tds': 'http://www.onvif.org/ver10/device/wsdl',
    'trt': 'http://www.onvif.org/ver10/media/wsdl',
    'tptz': 'http://www.onvif.org/ver20/ptz/wsdl',
    'tt': 'http://www.onvif.org/ver10/schema',
    'wsa': 'http://www.w3.org/2005/08/addressing',
    'wsse': 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd',
    'wsu': 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd'
}

# Device configuration
DEVICE_CONFIG = {
    'manufacturer': 'ONVIF Server',
    'model': 'FastAPI Camera',
    'firmware_version': '1.0.0',
    'serial_number': 'ONVIF-001',
    'hardware_id': 'HW-001'
}

# Media profiles
MEDIA_PROFILES = {
    'Profile_1': {
        'token': 'Profile_1',
        'name': 'Main Stream',
        'video_encoder': {
            'encoding': 'H264',
            'resolution': {'width': 1920, 'height': 1080},
            'framerate': 30,
            'bitrate': 4000
        },
        'audio_encoder': {
            'encoding': 'AAC',
            'bitrate': 128,
            'sample_rate': 48000
        }
    },
    'Profile_2': {
        'token': 'Profile_2',
        'name': 'Sub Stream',
        'video_encoder': {
            'encoding': 'H264',
            'resolution': {'width': 640, 'height': 480},
            'framerate': 15,
            'bitrate': 1000
        }
    }
}

# Simple user authentication
USERS = {
    'admin': {
        'password': 'admin123',
        'role': 'Administrator'
    },
    'user': {
        'password': 'user123',
        'role': 'User'
    }
}

def create_password_digest(username: str, password: str, nonce: str, created: str) -> str:
    """Create WS-Security password digest"""
    # Decode base64 nonce
    nonce_bytes = base64.b64decode(nonce)
    
    # Create digest: Base64(SHA1(nonce + created + password))
    digest_input = nonce_bytes + created.encode('utf-8') + password.encode('utf-8')
    digest = hashlib.sha1(digest_input).digest()
    return base64.b64encode(digest).decode('utf-8')

def verify_wsse_credentials(security_header) -> Optional[str]:
    """Verify WS-Security username token credentials"""
    if security_header is None:
        return None
    
    try:
        # Extract username token elements
        username_token = security_header.find('.//{http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd}UsernameToken')
        if username_token is None:
            return None
            
        username_elem = username_token.find('.//{http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd}Username')
        password_elem = username_token.find('.//{http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd}Password')
        nonce_elem = username_token.find('.//{http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd}Nonce')
        created_elem = username_token.find('.//{http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd}Created')
        
        if not all([username_elem, password_elem]):
            return None
            
        username = username_elem.text
        password_digest = password_elem.text
        password_type = password_elem.get('Type', '')
        
        if username not in USERS:
            return None
            
        user_password = USERS[username]['password']
        
        # Check if it's digest authentication
        if 'PasswordDigest' in password_type and nonce_elem is not None and created_elem is not None:
            nonce = nonce_elem.text
            created = created_elem.text
            
            # Verify timestamp (should be within 5 minutes)
            try:
                created_time = datetime.fromisoformat(created.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                if abs((now - created_time).total_seconds()) > 300:  # 5 minutes
                    return None
            except ValueError:
                return None
            
            # Calculate expected digest
            expected_digest = create_password_digest(username, user_password, nonce, created)
            
            if password_digest == expected_digest:
                return username
        
        # Check if it's plain text password (less secure but supported)
        elif 'PasswordText' in password_type or not password_type:
            if password_digest == user_password:
                return username
    
    except Exception:
        pass
    
    return None

def authenticate_request(xml_content: str) -> Optional[str]:
    """Authenticate ONVIF request using WS-Security"""
    try:
        root = ET.fromstring(xml_content)
        
        # Find security header
        security_header = root.find('.//{http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd}Security')
        
        return verify_wsse_credentials(security_header)
    except ET.ParseError:
        return None

def create_soap_fault(fault_code: str, fault_string: str) -> str:
    """Create SOAP fault response for authentication errors"""
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
    <soap:Body>
        <soap:Fault>
            <soap:Code>
                <soap:Value>soap:{fault_code}</soap:Value>
            </soap:Code>
            <soap:Reason>
                <soap:Text xml:lang="en">{fault_string}</soap:Text>
            </soap:Reason>
        </soap:Fault>
    </soap:Body>
</soap:Envelope>'''


def create_soap_response(body_content: str, action: str = None) -> str:
    """Parse SOAP request to extract action and parameters"""
    try:
        root = ET.fromstring(xml_content)
        
        # Find the action in the body
        body = root.find('.//{http://www.w3.org/2003/05/soap-envelope}Body')
        if body is not None:
            for child in body:
                return {
                    'action': child.tag.split('}')[-1] if '}' in child.tag else child.tag,
                    'namespace': child.tag.split('}')[0][1:] if '}' in child.tag else '',
                    'element': child
                }
    except ET.ParseError:
        pass
    
    return {'action': None, 'namespace': '', 'element': None}

def parse_soap_request(xml_content: str) -> Dict[str, Any]:
    """Parse SOAP request to extract action and parameters"""
    try:
        root = ET.fromstring(xml_content)
        
        # Find the action in the body
        body = root.find('.//{http://www.w3.org/2003/05/soap-envelope}Body')
        if body is not None:
            for child in body:
                return {
                    'action': child.tag.split('}')[-1] if '}' in child.tag else child.tag,
                    'namespace': child.tag.split('}')[0][1:] if '}' in child.tag else '',
                    'element': child
                }
    except ET.ParseError:
        pass
    
    return {'action': None, 'namespace': '', 'element': None}
# Device Management Service
@app.post("/onvif/device_service")
async def device_service(request: Request):
    """Handle Device Management Service requests"""
    xml_content = await request.body()
    xml_str = xml_content.decode('utf-8')
    
    # Authenticate request
    user = authenticate_request(xml_str)
    if user is None:
        fault_response = create_soap_fault("Sender", "Authentication failed")
        return Response(content=fault_response, media_type="application/soap+xml", status_code=401)
    
    soap_request = parse_soap_request(xml_str)
    
    action = soap_request['action']
    
    if action == 'GetDeviceInformation':
        body_content = f'''
        <tds:GetDeviceInformationResponse>
            <tds:Manufacturer>{DEVICE_CONFIG['manufacturer']}</tds:Manufacturer>
            <tds:Model>{DEVICE_CONFIG['model']}</tds:Model>
            <tds:FirmwareVersion>{DEVICE_CONFIG['firmware_version']}</tds:FirmwareVersion>
            <tds:SerialNumber>{DEVICE_CONFIG['serial_number']}</tds:SerialNumber>
            <tds:HardwareId>{DEVICE_CONFIG['hardware_id']}</tds:HardwareId>
        </tds:GetDeviceInformationResponse>'''
        
    elif action == 'GetCapabilities':
        body_content = '''
        <tds:GetCapabilitiesResponse>
            <tds:Capabilities>
                <tt:Device>
                    <tt:XAddr>http://localhost:8000/onvif/device_service</tt:XAddr>
                    <tt:Network>
                        <tt:IPFilter>false</tt:IPFilter>
                        <tt:ZeroConfiguration>false</tt:ZeroConfiguration>
                        <tt:IPVersion6>false</tt:IPVersion6>
                        <tt:DynDNS>false</tt:DynDNS>
                    </tt:Network>
                    <tt:System>
                        <tt:DiscoveryResolve>false</tt:DiscoveryResolve>
                        <tt:DiscoveryBye>false</tt:DiscoveryBye>
                        <tt:RemoteDiscovery>false</tt:RemoteDiscovery>
                        <tt:SystemBackup>false</tt:SystemBackup>
                        <tt:SystemLogging>false</tt:SystemLogging>
                        <tt:FirmwareUpgrade>false</tt:FirmwareUpgrade>
                    </tt:System>
                    <tt:IO>
                        <tt:InputConnectors>0</tt:InputConnectors>
                        <tt:RelayOutputs>0</tt:RelayOutputs>
                    </tt:IO>
                    <tt:Security>
                        <tt:TLS1.1>false</tt:TLS1.1>
                        <tt:TLS1.2>true</tt:TLS1.2>
                        <tt:OnboardKeyGeneration>false</tt:OnboardKeyGeneration>
                        <tt:AccessPolicyConfig>false</tt:AccessPolicyConfig>
                        <tt:X.509Token>false</tt:X.509Token>
                        <tt:SAMLToken>false</tt:SAMLToken>
                        <tt:KerberosToken>false</tt:KerberosToken>
                        <tt:RELToken>false</tt:RELToken>
                    </tt:Security>
                </tt:Device>
                <tt:Media>
                    <tt:XAddr>http://localhost:8000/onvif/media_service</tt:XAddr>
                    <tt:StreamingCapabilities>
                        <tt:RTPMulticast>false</tt:RTPMulticast>
                        <tt:RTP_TCP>true</tt:RTP_TCP>
                        <tt:RTP_RTSP_TCP>true</tt:RTP_RTSP_TCP>
                    </tt:StreamingCapabilities>
                </tt:Media>
                <tt:PTZ>
                    <tt:XAddr>http://localhost:8000/onvif/ptz_service</tt:XAddr>
                </tt:PTZ>
            </tds:Capabilities>
        </tds:GetCapabilitiesResponse>'''
        
    elif action == 'GetServices':
        body_content = '''
        <tds:GetServicesResponse>
            <tds:Service>
                <tds:Namespace>http://www.onvif.org/ver10/device/wsdl</tds:Namespace>
                <tds:XAddr>http://localhost:8000/onvif/device_service</tds:XAddr>
                <tds:Version>
                    <tt:Major>2</tt:Major>
                    <tt:Minor>5</tt:Minor>
                </tds:Version>
            </tds:Service>
            <tds:Service>
                <tds:Namespace>http://www.onvif.org/ver10/media/wsdl</tds:Namespace>
                <tds:XAddr>http://localhost:8000/onvif/media_service</tds:XAddr>
                <tds:Version>
                    <tt:Major>2</tt:Major>
                    <tt:Minor>5</tt:Minor>
                </tds:Version>
            </tds:Service>
            <tds:Service>
                <tds:Namespace>http://www.onvif.org/ver20/ptz/wsdl</tds:Namespace>
                <tds:XAddr>http://localhost:8000/onvif/ptz_service</tds:XAddr>
                <tds:Version>
                    <tt:Major>2</tt:Major>
                    <tt:Minor>5</tt:Minor>
                </tds:Version>
            </tds:Service>
        </tds:GetServicesResponse>'''
        
    elif action == 'GetSystemDateAndTime':
        current_time = datetime.now(timezone.utc)
        body_content = f'''
        <tds:GetSystemDateAndTimeResponse>
            <tds:SystemDateAndTime>
                <tt:DateTimeType>NTP</tt:DateTimeType>
                <tt:DaylightSavings>false</tt:DaylightSavings>
                <tt:TimeZone>
                    <tt:TZ>UTC</tt:TZ>
                </tt:TimeZone>
                <tt:UTCDateTime>
                    <tt:Time>
                        <tt:Hour>{current_time.hour}</tt:Hour>
                        <tt:Minute>{current_time.minute}</tt:Minute>
                        <tt:Second>{current_time.second}</tt:Second>
                    </tt:Time>
                    <tt:Date>
                        <tt:Year>{current_time.year}</tt:Year>
                        <tt:Month>{current_time.month}</tt:Month>
                        <tt:Day>{current_time.day}</tt:Day>
                    </tt:Date>
                </tt:UTCDateTime>
            </tds:SystemDateAndTime>
        </tds:GetSystemDateAndTimeResponse>'''
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported action: {action}")
    
    response_xml = create_soap_response(body_content)
    return Response(content=response_xml, media_type="application/soap+xml")

# Media Service
@app.post("/onvif/media_service")
async def media_service(request: Request):
    """Handle Media Service requests"""
    xml_content = await request.body()
    xml_str = xml_content.decode('utf-8')
    
    # Authenticate request
    user = authenticate_request(xml_str)
    if user is None:
        fault_response = create_soap_fault("Sender", "Authentication failed")
        return Response(content=fault_response, media_type="application/soap+xml", status_code=401)
    
    soap_request = parse_soap_request(xml_str)
    
    action = soap_request['action']
    
    if action == 'GetProfiles':
        profiles_xml = ''
        for profile_token, profile_data in MEDIA_PROFILES.items():
            video_config = profile_data['video_encoder']
            profiles_xml += f'''
            <trt:Profiles token="{profile_token}" fixed="true">
                <tt:Name>{profile_data['name']}</tt:Name>
                <tt:VideoSourceConfiguration token="VideoSource_1">
                    <tt:Name>Primary Video Source</tt:Name>
                    <tt:UseCount>1</tt:UseCount>
                    <tt:SourceToken>VideoSource_1</tt:SourceToken>
                    <tt:Bounds x="0" y="0" width="{video_config['resolution']['width']}" height="{video_config['resolution']['height']}"/>
                </tt:VideoSourceConfiguration>
                <tt:VideoEncoderConfiguration token="VideoEncoder_{profile_token}">
                    <tt:Name>{profile_data['name']} Video Encoder</tt:Name>
                    <tt:UseCount>1</tt:UseCount>
                    <tt:Encoding>{video_config['encoding']}</tt:Encoding>
                    <tt:Resolution>
                        <tt:Width>{video_config['resolution']['width']}</tt:Width>
                        <tt:Height>{video_config['resolution']['height']}</tt:Height>
                    </tt:Resolution>
                    <tt:Quality>5</tt:Quality>
                    <tt:RateControl>
                        <tt:FrameRateLimit>{video_config['framerate']}</tt:FrameRateLimit>
                        <tt:EncodingInterval>1</tt:EncodingInterval>
                        <tt:BitrateLimit>{video_config['bitrate']}</tt:BitrateLimit>
                    </tt:RateControl>
                </tt:VideoEncoderConfiguration>'''
            
            if 'audio_encoder' in profile_data:
                audio_config = profile_data['audio_encoder']
                profiles_xml += f'''
                <tt:AudioEncoderConfiguration token="AudioEncoder_{profile_token}">
                    <tt:Name>{profile_data['name']} Audio Encoder</tt:Name>
                    <tt:UseCount>1</tt:UseCount>
                    <tt:Encoding>{audio_config['encoding']}</tt:Encoding>
                    <tt:Bitrate>{audio_config['bitrate']}</tt:Bitrate>
                    <tt:SampleRate>{audio_config['sample_rate']}</tt:SampleRate>
                </tt:AudioEncoderConfiguration>'''
            
            profiles_xml += '''
            </trt:Profiles>'''
        
        body_content = f'''
        <trt:GetProfilesResponse>
            {profiles_xml}
        </trt:GetProfilesResponse>'''
        
    elif action == 'GetStreamUri':
        # Extract profile token from request
        element = soap_request['element']
        profile_token = None
        if element is not None:
            profile_ref = element.find('.//{http://www.onvif.org/ver10/media/wsdl}ProfileToken')
            if profile_ref is not None:
                profile_token = profile_ref.text
        
        if not profile_token or profile_token not in MEDIA_PROFILES:
            profile_token = 'Profile_1'  # Default profile
        
        stream_uri = f"rtsp://localhost:554/stream/{profile_token}"
        
        body_content = f'''
        <trt:GetStreamUriResponse>
            <trt:MediaUri>
                <tt:Uri>{stream_uri}</tt:Uri>
                <tt:InvalidAfterConnect>false</tt:InvalidAfterConnect>
                <tt:InvalidAfterReboot>false</tt:InvalidAfterReboot>
                <tt:Timeout>PT30S</tt:Timeout>
            </trt:MediaUri>
        </trt:GetStreamUriResponse>'''
        
    elif action == 'GetVideoSources':
        body_content = '''
        <trt:GetVideoSourcesResponse>
            <trt:VideoSources token="VideoSource_1">
                <tt:Framerate>30</tt:Framerate>
                <tt:Resolution>
                    <tt:Width>1920</tt:Width>
                    <tt:Height>1080</tt:Height>
                </tt:Resolution>
            </trt:VideoSources>
        </trt:GetVideoSourcesResponse>'''
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported action: {action}")
    
    response_xml = create_soap_response(body_content)
    return Response(content=response_xml, media_type="application/soap+xml")

# PTZ Service
@app.post("/onvif/ptz_service")
async def ptz_service(request: Request):
    """Handle PTZ Service requests"""
    xml_content = await request.body()
    xml_str = xml_content.decode('utf-8')
    
    # Authenticate request
    user = authenticate_request(xml_str)
    if user is None:
        fault_response = create_soap_fault("Sender", "Authentication failed")
        return Response(content=fault_response, media_type="application/soap+xml", status_code=401)
    
    soap_request = parse_soap_request(xml_str)
    
    action = soap_request['action']
    
    if action == 'GetConfigurations':
        body_content = '''
        <tptz:GetConfigurationsResponse>
            <tptz:PTZConfiguration token="PTZ_1">
                <tt:Name>Primary PTZ Configuration</tt:Name>
                <tt:UseCount>1</tt:UseCount>
                <tt:NodeToken>PTZ_Node_1</tt:NodeToken>
                <tt:DefaultAbsolutePantTiltPositionSpace>http://www.onvif.org/ver10/tptz/PanTiltSpaces/PositionGenericSpace</tt:DefaultAbsolutePantTiltPositionSpace>
                <tt:DefaultAbsoluteZoomPositionSpace>http://www.onvif.org/ver10/tptz/ZoomSpaces/PositionGenericSpace</tt:DefaultAbsoluteZoomPositionSpace>
                <tt:DefaultRelativePanTiltTranslationSpace>http://www.onvif.org/ver10/tptz/PanTiltSpaces/TranslationGenericSpace</tt:DefaultRelativePanTiltTranslationSpace>
                <tt:DefaultRelativeZoomTranslationSpace>http://www.onvif.org/ver10/tptz/ZoomSpaces/TranslationGenericSpace</tt:DefaultRelativeZoomTranslationSpace>
                <tt:DefaultContinuousPanTiltVelocitySpace>http://www.onvif.org/ver10/tptz/PanTiltSpaces/VelocityGenericSpace</tt:DefaultContinuousPanTiltVelocitySpace>
                <tt:DefaultContinuousZoomVelocitySpace>http://www.onvif.org/ver10/tptz/ZoomSpaces/VelocityGenericSpace</tt:DefaultContinuousZoomVelocitySpace>
                <tt:DefaultPTZSpeed>
                    <tt:PanTilt x="0.1" y="0.1" space="http://www.onvif.org/ver10/tptz/PanTiltSpaces/GenericSpeedSpace"/>
                    <tt:Zoom x="0.1" space="http://www.onvif.org/ver10/tptz/ZoomSpaces/ZoomGenericSpeedSpace"/>
                </tt:DefaultPTZSpeed>
                <tt:DefaultPTZTimeout>PT5S</tt:DefaultPTZTimeout>
            </tptz:PTZConfiguration>
        </tptz:GetConfigurationsResponse>'''
        
    elif action == 'GetNodes':
        body_content = '''
        <tptz:GetNodesResponse>
            <tptz:PTZNode token="PTZ_Node_1" FixedHomePosition="false">
                <tt:Name>Primary PTZ Node</tt:Name>
                <tt:SupportedPTZSpaces>
                    <tt:AbsolutePanTiltPositionSpace>
                        <tt:URI>http://www.onvif.org/ver10/tptz/PanTiltSpaces/PositionGenericSpace</tt:URI>
                        <tt:XRange>
                            <tt:Min>-180</tt:Min>
                            <tt:Max>180</tt:Max>
                        </tt:XRange>
                        <tt:YRange>
                            <tt:Min>-90</tt:Min>
                            <tt:Max>90</tt:Max>
                        </tt:YRange>
                    </tt:AbsolutePanTiltPositionSpace>
                    <tt:AbsoluteZoomPositionSpace>
                        <tt:URI>http://www.onvif.org/ver10/tptz/ZoomSpaces/PositionGenericSpace</tt:URI>
                        <tt:XRange>
                            <tt:Min>0</tt:Min>
                            <tt:Max>1</tt:Max>
                        </tt:XRange>
                    </tt:AbsoluteZoomPositionSpace>
                </tt:SupportedPTZSpaces>
                <tt:MaximumNumberOfPresets>16</tt:MaximumNumberOfPresets>
                <tt:HomeSupported>true</tt:HomeSupported>
            </tptz:PTZNode>
        </tptz:GetNodesResponse>'''
        
    elif action == 'GetStatus':
        body_content = '''
        <tptz:GetStatusResponse>
            <tptz:PTZStatus>
                <tt:Position>
                    <tt:PanTilt x="0.0" y="0.0" space="http://www.onvif.org/ver10/tptz/PanTiltSpaces/PositionGenericSpace"/>
                    <tt:Zoom x="0.0" space="http://www.onvif.org/ver10/tptz/ZoomSpaces/PositionGenericSpace"/>
                </tt:Position>
                <tt:MoveStatus>
                    <tt:PanTilt>IDLE</tt:PanTilt>
                    <tt:Zoom>IDLE</tt:Zoom>
                </tt:MoveStatus>
                <tt:UtcTime>2024-01-01T00:00:00Z</tt:UtcTime>
            </tptz:PTZStatus>
        </tptz:GetStatusResponse>'''
        
    elif action == 'AbsoluteMove':
        body_content = '''
        <tptz:AbsoluteMoveResponse>
        </tptz:AbsoluteMoveResponse>'''
        
    elif action == 'RelativeMove':
        body_content = '''
        <tptz:RelativeMoveResponse>
        </tptz:RelativeMoveResponse>'''
        
    elif action == 'ContinuousMove':
        body_content = '''
        <tptz:ContinuousMoveResponse>
        </tptz:ContinuousMoveResponse>'''
        
    elif action == 'Stop':
        body_content = '''
        <tptz:StopResponse>
        </tptz:StopResponse>'''
    
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported action: {action}")
    
    response_xml = create_soap_response(body_content)
    return Response(content=response_xml, media_type="application/soap+xml")

# WS-Discovery endpoint for device discovery
@app.get("/onvif/device_service", response_class=Response)
async def device_service_wsdl():
    """Return device service WSDL for discovery"""
    wsdl_content = '''<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://schemas.xmlsoap.org/wsdl/"
             xmlns:tds="http://www.onvif.org/ver10/device/wsdl"
             targetNamespace="http://www.onvif.org/ver10/device/wsdl">
    <types>
        <!-- ONVIF Device Management Schema -->
    </types>
    <message name="GetDeviceInformationRequest"/>
    <message name="GetDeviceInformationResponse"/>
    <portType name="Device">
        <operation name="GetDeviceInformation">
            <input message="tds:GetDeviceInformationRequest"/>
            <output message="tds:GetDeviceInformationResponse"/>
        </operation>
    </portType>
    <binding name="DeviceBinding" type="tds:Device">
        <!-- SOAP binding details -->
    </binding>
    <service name="DeviceService">
        <port name="DevicePort" binding="tds:DeviceBinding">
            <soap:address location="http://localhost:8000/onvif/device_service"/>
        </port>
    </service>
</definitions>'''
    
    return Response(content=wsdl_content, media_type="text/xml")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "ONVIF Server"}

# Root endpoint with server information
@app.get("/")
async def root():
    """Root endpoint with server information"""
    return {
        "service": "ONVIF Service Server",
        "version": "1.0.0",
        "endpoints": {
            "device_service": "/onvif/device_service",
            "media_service": "/onvif/media_service", 
            "ptz_service": "/onvif/ptz_service"
        },
        "authentication": "HTTP Basic Auth required",
        "supported_operations": {
            "device": ["GetDeviceInformation", "GetCapabilities", "GetServices", "GetSystemDateAndTime"],
            "media": ["GetProfiles", "GetStreamUri", "GetVideoSources"],
            "ptz": ["GetConfigurations", "GetNodes", "GetStatus", "AbsoluteMove", "RelativeMove", "ContinuousMove", "Stop"]
        }
    }

if __name__ == "__main__":
    print("Starting ONVIF Service Server...")
    print("Default credentials:")
    print("  Username: admin, Password: admin123")
    print("  Username: user, Password: user123")
    print("\nAvailable endpoints:")
    print("  Device Service: http://localhost:8000/onvif/device_service")
    print("  Media Service: http://localhost:8000/onvif/media_service")
    print("  PTZ Service: http://localhost:8000/onvif/ptz_service")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)