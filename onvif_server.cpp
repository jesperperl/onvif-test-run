#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <memory>
#include <thread>
#include <mutex>
#include <chrono>
#include <sstream>
#include <ctime>
#include <iomanip>

// Basic HTTP server functionality
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstring>

class OnvifServer {
private:
    int server_socket;
    int port;
    std::string device_uuid;
    std::string device_name;
    std::string manufacturer;
    std::string model;
    std::string serial_number;
    std::string firmware_version;
    
    // Media profiles
    struct MediaProfile {
        std::string token;
        std::string name;
        std::string video_encoder_token;
        std::string audio_encoder_token;
        int width;
        int height;
        int framerate;
        int bitrate;
    };
    
    std::vector<MediaProfile> media_profiles;
    std::mutex server_mutex;
    bool running;

public:
    OnvifServer(int port = 8080) : port(port), running(false) {
        device_uuid = "urn:uuid:12345678-1234-1234-1234-123456789012";
        device_name = "ONVIF Camera";
        manufacturer = "Sample Manufacturer";
        model = "Sample Model";
        serial_number = "123456789";
        firmware_version = "1.0.0";
        
        // Initialize default media profiles
        initializeMediaProfiles();
    }
    
    ~OnvifServer() {
        stop();
    }
    
private:
    void initializeMediaProfiles() {
        MediaProfile profile1;
        profile1.token = "Profile_1";
        profile1.name = "MainStream";
        profile1.video_encoder_token = "VideoEncoder_1";
        profile1.audio_encoder_token = "AudioEncoder_1";
        profile1.width = 1920;
        profile1.height = 1080;
        profile1.framerate = 30;
        profile1.bitrate = 4000000;
        
        MediaProfile profile2;
        profile2.token = "Profile_2";
        profile2.name = "SubStream";
        profile2.video_encoder_token = "VideoEncoder_2";
        profile2.audio_encoder_token = "AudioEncoder_2";
        profile2.width = 640;
        profile2.height = 480;
        profile2.framerate = 15;
        profile2.bitrate = 1000000;
        
        media_profiles.push_back(profile1);
        media_profiles.push_back(profile2);
    }
    
    std::string getCurrentTime() {
        auto now = std::chrono::system_clock::now();
        auto time_t = std::chrono::system_clock::to_time_t(now);
        std::stringstream ss;
        ss << std::put_time(std::gmtime(&time_t), "%Y-%m-%dT%H:%M:%SZ");
        return ss.str();
    }
    
    std::string generateSoapEnvelope(const std::string& body) {
        return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
               "<SOAP-ENV:Envelope xmlns:SOAP-ENV=\"http://www.w3.org/2003/05/soap-envelope\" "
               "xmlns:tds=\"http://www.onvif.org/ver10/device/wsdl\" "
               "xmlns:trt=\"http://www.onvif.org/ver10/media/wsdl\" "
               "xmlns:tptz=\"http://www.onvif.org/ver20/ptz/wsdl\">\n"
               "<SOAP-ENV:Body>\n" + body + "</SOAP-ENV:Body>\n"
               "</SOAP-ENV:Envelope>";
    }
    
    std::string handleGetDeviceInformation() {
        std::string body = "<tds:GetDeviceInformationResponse>\n"
                          "<tds:Manufacturer>" + manufacturer + "</tds:Manufacturer>\n"
                          "<tds:Model>" + model + "</tds:Model>\n"
                          "<tds:FirmwareVersion>" + firmware_version + "</tds:FirmwareVersion>\n"
                          "<tds:SerialNumber>" + serial_number + "</tds:SerialNumber>\n"
                          "<tds:HardwareId>" + device_uuid + "</tds:HardwareId>\n"
                          "</tds:GetDeviceInformationResponse>";
        return generateSoapEnvelope(body);
    }
    
    std::string handleGetCapabilities() {
        std::string body = "<tds:GetCapabilitiesResponse>\n"
                          "<tds:Capabilities>\n"
                          "<tds:Device>\n"
                          "<tds:XAddr>http://localhost:" + std::to_string(port) + "/onvif/device_service</tds:XAddr>\n"
                          "<tds:Network>\n"
                          "<tds:IPFilter>false</tds:IPFilter>\n"
                          "<tds:ZeroConfiguration>false</tds:ZeroConfiguration>\n"
                          "<tds:IPVersion6>false</tds:IPVersion6>\n"
                          "<tds:DynDNS>false</tds:DynDNS>\n"
                          "</tds:Network>\n"
                          "<tds:System>\n"
                          "<tds:DiscoveryResolve>false</tds:DiscoveryResolve>\n"
                          "<tds:DiscoveryBye>false</tds:DiscoveryBye>\n"
                          "<tds:RemoteDiscovery>false</tds:RemoteDiscovery>\n"
                          "<tds:SystemBackup>false</tds:SystemBackup>\n"
                          "<tds:SystemLogging>false</tds:SystemLogging>\n"
                          "<tds:FirmwareUpgrade>false</tds:FirmwareUpgrade>\n"
                          "</tds:System>\n"
                          "<tds:IO>\n"
                          "<tds:InputConnectors>0</tds:InputConnectors>\n"
                          "<tds:RelayOutputs>0</tds:RelayOutputs>\n"
                          "</tds:IO>\n"
                          "<tds:Security>\n"
                          "<tds:TLS1.1>false</tds:TLS1.1>\n"
                          "<tds:TLS1.2>true</tds:TLS1.2>\n"
                          "<tds:OnboardKeyGeneration>false</tds:OnboardKeyGeneration>\n"
                          "<tds:AccessPolicyConfig>false</tds:AccessPolicyConfig>\n"
                          "<tds:X.509Token>false</tds:X.509Token>\n"
                          "<tds:SAMLToken>false</tds:SAMLToken>\n"
                          "<tds:KerberosToken>false</tds:KerberosToken>\n"
                          "<tds:RELToken>false</tds:RELToken>\n"
                          "</tds:Security>\n"
                          "</tds:Device>\n"
                          "<tds:Media>\n"
                          "<tds:XAddr>http://localhost:" + std::to_string(port) + "/onvif/media_service</tds:XAddr>\n"
                          "<tds:StreamingCapabilities>\n"
                          "<tds:RTPMulticast>false</tds:RTPMulticast>\n"
                          "<tds:RTP_TCP>true</tds:RTP_TCP>\n"
                          "<tds:RTP_RTSP_TCP>true</tds:RTP_RTSP_TCP>\n"
                          "</tds:StreamingCapabilities>\n"
                          "</tds:Media>\n"
                          "<tds:PTZ>\n"
                          "<tds:XAddr>http://localhost:" + std::to_string(port) + "/onvif/ptz_service</tds:XAddr>\n"
                          "</tds:PTZ>\n"
                          "</tds:Capabilities>\n"
                          "</tds:GetCapabilitiesResponse>";
        return generateSoapEnvelope(body);
    }
    
    std::string handleGetProfiles() {
        std::string profiles_xml;
        for (const auto& profile : media_profiles) {
            profiles_xml += "<trt:Profiles token=\"" + profile.token + "\" fixed=\"true\">\n"
                           "<trt:Name>" + profile.name + "</trt:Name>\n"
                           "<trt:VideoSourceConfiguration token=\"VideoSource_1\" fixed=\"true\">\n"
                           "<trt:Name>VideoSourceConfig</trt:Name>\n"
                           "<trt:UseCount>2</trt:UseCount>\n"
                           "<trt:SourceToken>VideoSource_1</trt:SourceToken>\n"
                           "<trt:Bounds x=\"0\" y=\"0\" width=\"" + std::to_string(profile.width) + "\" height=\"" + std::to_string(profile.height) + "\"/>\n"
                           "</trt:VideoSourceConfiguration>\n"
                           "<trt:VideoEncoderConfiguration token=\"" + profile.video_encoder_token + "\" fixed=\"true\">\n"
                           "<trt:Name>VideoEncoderConfig</trt:Name>\n"
                           "<trt:UseCount>1</trt:UseCount>\n"
                           "<trt:Encoding>H264</trt:Encoding>\n"
                           "<trt:Resolution>\n"
                           "<trt:Width>" + std::to_string(profile.width) + "</trt:Width>\n"
                           "<trt:Height>" + std::to_string(profile.height) + "</trt:Height>\n"
                           "</trt:Resolution>\n"
                           "<trt:Quality>1</trt:Quality>\n"
                           "<trt:RateControl>\n"
                           "<trt:FrameRateLimit>" + std::to_string(profile.framerate) + "</trt:FrameRateLimit>\n"
                           "<trt:EncodingInterval>1</trt:EncodingInterval>\n"
                           "<trt:BitrateLimit>" + std::to_string(profile.bitrate) + "</trt:BitrateLimit>\n"
                           "</trt:RateControl>\n"
                           "<trt:H264>\n"
                           "<trt:GovLength>30</trt:GovLength>\n"
                           "<trt:H264Profile>Baseline</trt:H264Profile>\n"
                           "</trt:H264>\n"
                           "</trt:VideoEncoderConfiguration>\n"
                           "</trt:Profiles>\n";
        }
        
        std::string body = "<trt:GetProfilesResponse>\n" + profiles_xml + "</trt:GetProfilesResponse>";
        return generateSoapEnvelope(body);
    }
    
    std::string handleGetStreamUri() {
        std::string body = "<trt:GetStreamUriResponse>\n"
                          "<trt:MediaUri>\n"
                          "<trt:Uri>rtsp://localhost:" + std::to_string(port + 1) + "/stream1</trt:Uri>\n"
                          "<trt:InvalidAfterConnect>false</trt:InvalidAfterConnect>\n"
                          "<trt:InvalidAfterReboot>false</trt:InvalidAfterReboot>\n"
                          "<trt:Timeout>PT60S</trt:Timeout>\n"
                          "</trt:MediaUri>\n"
                          "</trt:GetStreamUriResponse>";
        return generateSoapEnvelope(body);
    }
    
    std::string handleGetSystemDateAndTime() {
        std::string current_time = getCurrentTime();
        std::string body = "<tds:GetSystemDateAndTimeResponse>\n"
                          "<tds:SystemDateAndTime>\n"
                          "<tds:DateTimeType>Manual</tds:DateTimeType>\n"
                          "<tds:DaylightSavings>false</tds:DaylightSavings>\n"
                          "<tds:TimeZone>\n"
                          "<tds:TZ>UTC</tds:TZ>\n"
                          "</tds:TimeZone>\n"
                          "<tds:UTCDateTime>\n"
                          "<tds:Time>\n"
                          "<tds:Hour>12</tds:Hour>\n"
                          "<tds:Minute>0</tds:Minute>\n"
                          "<tds:Second>0</tds:Second>\n"
                          "</tds:Time>\n"
                          "<tds:Date>\n"
                          "<tds:Year>2024</tds:Year>\n"
                          "<tds:Month>1</tds:Month>\n"
                          "<tds:Day>1</tds:Day>\n"
                          "</tds:Date>\n"
                          "</tds:UTCDateTime>\n"
                          "</tds:SystemDateAndTime>\n"
                          "</tds:GetSystemDateAndTimeResponse>";
        return generateSoapEnvelope(body);
    }
    
    std::string handlePTZGetConfigurations() {
        std::string body = "<tptz:GetConfigurationsResponse>\n"
                          "<tptz:PTZConfiguration token=\"PTZConfig_1\">\n"
                          "<tptz:Name>PTZ Configuration</tptz:Name>\n"
                          "<tptz:UseCount>1</tptz:UseCount>\n"
                          "<tptz:NodeToken>PTZNode_1</tptz:NodeToken>\n"
                          "<tptz:DefaultAbsolutePantTiltPositionSpace>http://www.onvif.org/ver10/tptz/PanTiltSpaces/PositionGenericSpace</tptz:DefaultAbsolutePantTiltPositionSpace>\n"
                          "<tptz:DefaultAbsoluteZoomPositionSpace>http://www.onvif.org/ver10/tptz/ZoomSpaces/PositionGenericSpace</tptz:DefaultAbsoluteZoomPositionSpace>\n"
                          "<tptz:DefaultRelativePanTiltTranslationSpace>http://www.onvif.org/ver10/tptz/PanTiltSpaces/TranslationGenericSpace</tptz:DefaultRelativePanTiltTranslationSpace>\n"
                          "<tptz:DefaultRelativeZoomTranslationSpace>http://www.onvif.org/ver10/tptz/ZoomSpaces/TranslationGenericSpace</tptz:DefaultRelativeZoomTranslationSpace>\n"
                          "<tptz:DefaultContinuousPanTiltVelocitySpace>http://www.onvif.org/ver10/tptz/PanTiltSpaces/VelocityGenericSpace</tptz:DefaultContinuousPanTiltVelocitySpace>\n"
                          "<tptz:DefaultContinuousZoomVelocitySpace>http://www.onvif.org/ver10/tptz/ZoomSpaces/VelocityGenericSpace</tptz:DefaultContinuousZoomVelocitySpace>\n"
                          "<tptz:DefaultPTZSpeed>\n"
                          "<tptz:PanTilt x=\"1.0\" y=\"1.0\" space=\"http://www.onvif.org/ver10/tptz/PanTiltSpaces/GenericSpeedSpace\"/>\n"
                          "<tptz:Zoom x=\"1.0\" space=\"http://www.onvif.org/ver10/tptz/ZoomSpaces/ZoomGenericSpeedSpace\"/>\n"
                          "</tptz:DefaultPTZSpeed>\n"
                          "<tptz:DefaultPTZTimeout>PT5S</tptz:DefaultPTZTimeout>\n"
                          "<tptz:PanTiltLimits>\n"
                          "<tptz:Range>\n"
                          "<tptz:URI>http://www.onvif.org/ver10/tptz/PanTiltSpaces/PositionGenericSpace</tptz:URI>\n"
                          "<tptz:XRange>\n"
                          "<tptz:Min>-1.0</tptz:Min>\n"
                          "<tptz:Max>1.0</tptz:Max>\n"
                          "</tptz:XRange>\n"
                          "<tptz:YRange>\n"
                          "<tptz:Min>-1.0</tptz:Min>\n"
                          "<tptz:Max>1.0</tptz:Max>\n"
                          "</tptz:YRange>\n"
                          "</tptz:Range>\n"
                          "</tptz:PanTiltLimits>\n"
                          "<tptz:ZoomLimits>\n"
                          "<tptz:Range>\n"
                          "<tptz:URI>http://www.onvif.org/ver10/tptz/ZoomSpaces/PositionGenericSpace</tptz:URI>\n"
                          "<tptz:XRange>\n"
                          "<tptz:Min>0.0</tptz:Min>\n"
                          "<tptz:Max>1.0</tptz:Max>\n"
                          "</tptz:XRange>\n"
                          "</tptz:Range>\n"
                          "</tptz:ZoomLimits>\n"
                          "</tptz:PTZConfiguration>\n"
                          "</tptz:GetConfigurationsResponse>";
        return generateSoapEnvelope(body);
    }
    
    std::string processRequest(const std::string& request) {
        std::string response;
        
        if (request.find("GetDeviceInformation") != std::string::npos) {
            response = handleGetDeviceInformation();
        }
        else if (request.find("GetCapabilities") != std::string::npos) {
            response = handleGetCapabilities();
        }
        else if (request.find("GetProfiles") != std::string::npos) {
            response = handleGetProfiles();
        }
        else if (request.find("GetStreamUri") != std::string::npos) {
            response = handleGetStreamUri();
        }
        else if (request.find("GetSystemDateAndTime") != std::string::npos) {
            response = handleGetSystemDateAndTime();
        }
        else if (request.find("GetConfigurations") != std::string::npos) {
            response = handlePTZGetConfigurations();
        }
        else {
            // Default error response
            std::string body = "<SOAP-ENV:Fault>\n"
                              "<SOAP-ENV:Code>\n"
                              "<SOAP-ENV:Value>SOAP-ENV:Receiver</SOAP-ENV:Value>\n"
                              "</SOAP-ENV:Code>\n"
                              "<SOAP-ENV:Reason>\n"
                              "<SOAP-ENV:Text>Method not implemented</SOAP-ENV:Text>\n"
                              "</SOAP-ENV:Reason>\n"
                              "</SOAP-ENV:Fault>";
            response = generateSoapEnvelope(body);
        }
        
        return response;
    }
    
    void handleClient(int client_socket) {
        char buffer[4096] = {0};
        int bytes_read = read(client_socket, buffer, sizeof(buffer) - 1);
        
        if (bytes_read > 0) {
            std::string request(buffer);
            std::cout << "Received request:\n" << request << "\n\n";
            
            std::string soap_response = processRequest(request);
            
            std::string http_response = 
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: application/soap+xml; charset=utf-8\r\n"
                "Content-Length: " + std::to_string(soap_response.length()) + "\r\n"
                "Connection: close\r\n"
                "\r\n" + soap_response;
            
            send(client_socket, http_response.c_str(), http_response.length(), 0);
            std::cout << "Sent response:\n" << http_response << "\n\n";
        }
        
        close(client_socket);
    }

public:
    bool start() {
        server_socket = socket(AF_INET, SOCK_STREAM, 0);
        if (server_socket < 0) {
            std::cerr << "Error creating socket" << std::endl;
            return false;
        }
        
        int opt = 1;
        setsockopt(server_socket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
        
        struct sockaddr_in address;
        address.sin_family = AF_INET;
        address.sin_addr.s_addr = INADDR_ANY;
        address.sin_port = htons(port);
        
        if (bind(server_socket, (struct sockaddr*)&address, sizeof(address)) < 0) {
            std::cerr << "Bind failed" << std::endl;
            close(server_socket);
            return false;
        }
        
        if (listen(server_socket, 5) < 0) {
            std::cerr << "Listen failed" << std::endl;
            close(server_socket);
            return false;
        }
        
        running = true;
        std::cout << "ONVIF Server started on port " << port << std::endl;
        std::cout << "Device Service: http://localhost:" << port << "/onvif/device_service" << std::endl;
        std::cout << "Media Service: http://localhost:" << port << "/onvif/media_service" << std::endl;
        std::cout << "PTZ Service: http://localhost:" << port << "/onvif/ptz_service" << std::endl;
        
        return true;
    }
    
    void run() {
        while (running) {
            struct sockaddr_in client_address;
            socklen_t client_len = sizeof(client_address);
            
            int client_socket = accept(server_socket, (struct sockaddr*)&client_address, &client_len);
            if (client_socket >= 0) {
                std::thread client_thread(&OnvifServer::handleClient, this, client_socket);
                client_thread.detach();
            }
        }
    }
    
    void stop() {
        running = false;
        if (server_socket >= 0) {
            close(server_socket);
        }
    }
};

int main() {
    OnvifServer server(8080);
    
    if (!server.start()) {
        std::cerr << "Failed to start server" << std::endl;
        return -1;
    }
    
    std::cout << "Press Enter to stop the server..." << std::endl;
    
    // Start server in a separate thread
    std::thread server_thread(&OnvifServer::run, &server);
    
    // Wait for user input to stop
    std::cin.get();
    
    server.stop();
    server_thread.join();
    
    std::cout << "Server stopped" << std::endl;
    return 0;
}