package com.smartlearning.sessions;

import com.smartlearning.auth.AuthenticatedUserResolver;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.UUID;

@Validated
@RestController
@RequestMapping("/api/v1/sessions")
public class StudySessionController {

    private final StudySessionService service;
    private final AuthenticatedUserResolver userResolver;

    public StudySessionController(StudySessionService service, AuthenticatedUserResolver userResolver) {
        this.service = service;
        this.userResolver = userResolver;
    }

    @PostMapping({"", "/"})
    @ResponseStatus(HttpStatus.CREATED)
    public StudySessionResponse create(
            @AuthenticationPrincipal Jwt jwt,
            @Valid @RequestBody CreateSessionRequest request
    ) {
        return service.create(userResolver.requireUserId(jwt), request);
    }

    @GetMapping({"", "/"})
    public List<StudySessionResponse> list(
            @AuthenticationPrincipal Jwt jwt,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) OffsetDateTime dateFrom,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) OffsetDateTime dateTo,
            @RequestParam(defaultValue = "0") @Min(0) int offset,
            @RequestParam(defaultValue = "20") @Min(1) @Max(100) int limit
    ) {
        return service.list(userResolver.requireUserId(jwt), dateFrom, dateTo, offset, limit);
    }

    @GetMapping("/{sessionId}")
    public StudySessionResponse get(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable UUID sessionId
    ) {
        return service.get(userResolver.requireUserId(jwt), sessionId);
    }

    @PatchMapping("/{sessionId}/end")
    public StudySessionResponse end(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable UUID sessionId,
            @Valid @RequestBody EndSessionRequest request
    ) {
        return service.end(userResolver.requireUserId(jwt), sessionId, request);
    }
}
