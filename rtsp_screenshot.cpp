#include <opencv2/opencv.hpp>
#include <iostream>
#include <string>
#include <chrono>
#include <thread>

class RTSPScreenshot {
private:
    cv::VideoCapture cap;
    std::string rtspUrl;
    std::string username;
    std::string password;
    
public:
    RTSPScreenshot(const std::string& url) : rtspUrl(url) {}
    
    RTSPScreenshot(const std::string& url, const std::string& user, const std::string& pass) 
        : rtspUrl(url), username(user), password(pass) {}
    
    bool connect() {
        std::string finalUrl = rtspUrl;
        
        // If username and password are provided, construct authenticated URL
        if (!username.empty() && !password.empty()) {
            // Find the protocol part (rtsp://)
            size_t protocolEnd = rtspUrl.find("://");
            if (protocolEnd != std::string::npos) {
                std::string protocol = rtspUrl.substr(0, protocolEnd + 3);
                std::string remainder = rtspUrl.substr(protocolEnd + 3);
                finalUrl = protocol + username + ":" + password + "@" + remainder;
                std::cout << "Connecting to RTSP stream with authentication..." << std::endl;
            } else {
                std::cerr << "Error: Invalid RTSP URL format!" << std::endl;
                return false;
            }
        } else {
            std::cout << "Connecting to RTSP stream: " << rtspUrl << std::endl;
        }
        
        // Open the RTSP stream
        cap.open(finalUrl);
        
        if (!cap.isOpened()) {
            std::cerr << "Error: Could not open RTSP stream!" << std::endl;
            std::cerr << "Check URL, credentials, and network connectivity." << std::endl;
            return false;
        }
        
        // Set buffer size to reduce latency
        cap.set(cv::CAP_PROP_BUFFERSIZE, 1);
        
        // Optional: Set connection timeout (in milliseconds)
        cap.set(cv::CAP_PROP_OPEN_TIMEOUT_MSEC, 10000);
        
        std::cout << "Successfully connected to RTSP stream" << std::endl;
        return true;
    }
    
    bool captureScreenshot(const std::string& filename) {
        if (!cap.isOpened()) {
            std::cerr << "Error: RTSP stream is not open!" << std::endl;
            return false;
        }
        
        cv::Mat frame;
        
        // Try to read a few frames to get a stable image
        for (int i = 0; i < 5; i++) {
            cap >> frame;
            if (frame.empty()) {
                std::cerr << "Error: Could not capture frame from stream!" << std::endl;
                return false;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
        
        // Save the screenshot
        if (cv::imwrite(filename, frame)) {
            std::cout << "Screenshot saved successfully: " << filename << std::endl;
            std::cout << "Image size: " << frame.cols << "x" << frame.rows << std::endl;
            return true;
        } else {
            std::cerr << "Error: Could not save screenshot!" << std::endl;
            return false;
        }
    }
    
    void displayStream() {
        if (!cap.isOpened()) {
            std::cerr << "Error: RTSP stream is not open!" << std::endl;
            return;
        }
        
        cv::Mat frame;
        std::cout << "Displaying stream. Press 's' to save screenshot, 'q' to quit." << std::endl;
        
        while (true) {
            cap >> frame;
            if (frame.empty()) {
                std::cerr << "Error: Empty frame received!" << std::endl;
                break;
            }
            
            cv::imshow("RTSP Stream", frame);
            
            char key = cv::waitKey(30);
            if (key == 'q' || key == 'Q') {
                break;
            } else if (key == 's' || key == 'S') {
                // Generate timestamp-based filename
                auto now = std::chrono::system_clock::now();
                auto time_t = std::chrono::system_clock::to_time_t(now);
                auto tm = *std::localtime(&time_t);
                
                char timestamp[100];
                std::strftime(timestamp, sizeof(timestamp), "%Y%m%d_%H%M%S", &tm);
                
                std::string filename = "screenshot_" + std::string(timestamp) + ".jpg";
                cv::imwrite(filename, frame);
                std::cout << "Screenshot saved: " << filename << std::endl;
            }
        }
        
        cv::destroyAllWindows();
    }
    
    void disconnect() {
        if (cap.isOpened()) {
            cap.release();
            std::cout << "Disconnected from RTSP stream" << std::endl;
        }
    }
    
    ~RTSPScreenshot() {
        disconnect();
    }
};

int main(int argc, char* argv[]) {
    std::string rtspUrl;
    std::string outputFile = "screenshot.jpg";
    std::string username;
    std::string password;
    bool displayMode = false;
    
    // Parse command line arguments
    if (argc < 2) {
        std::cout << "Usage: " << argv[0] << " <rtsp_url> [options]" << std::endl;
        std::cout << "Options:" << std::endl;
        std::cout << "  --user <username>     RTSP username" << std::endl;
        std::cout << "  --pass <password>     RTSP password" << std::endl;
        std::cout << "  --output <filename>   Output filename (default: screenshot.jpg)" << std::endl;
        std::cout << "  --display            Interactive display mode" << std::endl;
        std::cout << std::endl;
        std::cout << "Examples:" << std::endl;
        std::cout << "  " << argv[0] << " rtsp://192.168.1.100:554/stream" << std::endl;
        std::cout << "  " << argv[0] << " rtsp://192.168.1.100:554/stream --user admin --pass 123456" << std::endl;
        std::cout << "  " << argv[0] << " rtsp://192.168.1.100:554/stream --user admin --pass 123456 --output camera1.png" << std::endl;
        std::cout << "  " << argv[0] << " rtsp://192.168.1.100:554/stream --user admin --pass 123456 --display" << std::endl;
        return -1;
    }
    
    rtspUrl = argv[1];
    
    // Parse additional arguments
    for (int i = 2; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--user" && i + 1 < argc) {
            username = argv[++i];
        } else if (arg == "--pass" && i + 1 < argc) {
            password = argv[++i];
        } else if (arg == "--output" && i + 1 < argc) {
            outputFile = argv[++i];
        } else if (arg == "--display") {
            displayMode = true;
        }
    }
    
    // Create RTSP screenshot object
    RTSPScreenshot rtspCapture(rtspUrl, username, password);
    
    // Connect to the stream
    if (!rtspCapture.connect()) {
        return -1;
    }
    
    if (displayMode) {
        // Display stream with interactive screenshot capability
        rtspCapture.displayStream();
    } else {
        // Capture a single screenshot
        if (!rtspCapture.captureScreenshot(outputFile)) {
            return -1;
        }
    }
    
    return 0;
}

// Compilation instructions:
// g++ -o rtsp_screenshot rtsp_screenshot.cpp `pkg-config --cflags --libs opencv4`
//
// Or if using older OpenCV:
// g++ -o rtsp_screenshot rtsp_screenshot.cpp `pkg-config --cflags --libs opencv`
//
// Make sure OpenCV is installed:
// Ubuntu/Debian: sudo apt-get install libopencv-dev
// CentOS/RHEL: sudo yum install opencv-devel
// macOS: brew install opencv
//
// Security Note: 
// - Credentials are passed via command line arguments and may be visible in process lists
// - For production use, consider reading credentials from environment variables or config files
// - Example with environment variables:
//   export RTSP_USER=admin
//   export RTSP_PASS=password123
//   ./rtsp_screenshot rtsp://192.168.1.100:554/stream