package com.smartlearning.logs;

import com.smartlearning.common.response.ApiResponse;
import jakarta.validation.Valid;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping("/api/v1/logs")
public class SystemLogController {

    private final SystemLogService service;
    private final String internalServiceToken;

    public SystemLogController(
            SystemLogService service,
            @Value("${app.internal.service-token}") String internalServiceToken
    ) {
        this.service = service;
        this.internalServiceToken = internalServiceToken;
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    public ApiResponse<SystemLogResponse> create(
            @RequestHeader(value = "X-Internal-Service-Token", required = false) String token,
            @Valid @RequestBody CreateSystemLogRequest request
    ) {
        if (token == null || !token.equals(internalServiceToken)) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Invalid internal service token");
        }

        return ApiResponse.ok("System log recorded", service.create(request));
    }
}
