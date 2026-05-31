package com.smartlearning.common.health;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import com.smartlearning.common.response.ApiResponse;
import org.springframework.web.bind.annotation.RequestMapping;
import java.util.Map;
@RestController
@RequestMapping("/api/health")
public class HealthController {
    @GetMapping
    public ApiResponse<Map<String, Object>> health(){
        return ApiResponse.ok("Spring boot  main backend is running", 
            Map.of(                        "service", "spring-backend",
                        "role", "main-orchestrator",
                        "status", "UP")
        );
    } 
}
