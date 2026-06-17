package com.smartlearning.blocks;

import com.smartlearning.auth.AuthenticatedUserResolver;
import jakarta.validation.Valid;
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
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.UUID;

@Validated
@RestController
@RequestMapping("/api/v1/blocks")
public class SessionBlockController {

    private final SessionBlockService service;
    private final AuthenticatedUserResolver userResolver;

    public SessionBlockController(SessionBlockService service, AuthenticatedUserResolver userResolver) {
        this.service = service;
        this.userResolver = userResolver;
    }

    @PostMapping({"", "/"})
    @ResponseStatus(HttpStatus.CREATED)
    public SessionBlockResponse create(
            @AuthenticationPrincipal Jwt jwt,
            @Valid @RequestBody CreateBlockRequest request
    ) {
        return service.create(userResolver.requireUserId(jwt), request);
    }

    @GetMapping("/session/{sessionId}")
    public List<SessionBlockResponse> listBySession(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable UUID sessionId
    ) {
        return service.listBySession(userResolver.requireUserId(jwt), sessionId);
    }

    @PostMapping("/session/{sessionId}/close-latest")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void closeLatest(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable UUID sessionId
    ) {
        service.closeLatest(userResolver.requireUserId(jwt), sessionId);
    }

    @PatchMapping("/{blockId}/heartbeat")
    public SessionBlockResponse heartbeat(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable UUID blockId,
            @Valid @RequestBody BlockHeartbeatRequest request
    ) {
        return service.heartbeat(userResolver.requireUserId(jwt), blockId, request);
    }
}
