package com.smartlearning.aiworker;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class AiWorkerProxyController {

    private final AiWorkerProxyService proxyService;

    public AiWorkerProxyController(AiWorkerProxyService proxyService) {
        this.proxyService = proxyService;
    }

    @RequestMapping({
            "/api/v1/monitoring",
            "/api/v1/monitoring/**",
            "/api/v1/ai-events",
            "/api/v1/ai-events/**",
            "/api/v1/alerts",
            "/api/v1/alerts/**"
    })
    public ResponseEntity<byte[]> proxy(
            @AuthenticationPrincipal Jwt jwt,
            HttpServletRequest request,
            @RequestBody(required = false) byte[] body
    ) {
        return proxyService.forward(request, body);
    }
}
