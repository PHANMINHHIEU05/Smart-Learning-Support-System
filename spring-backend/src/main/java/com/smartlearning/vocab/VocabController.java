package com.smartlearning.vocab;

import com.smartlearning.auth.AuthenticatedUserResolver;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
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
@RequestMapping("/api/v1/vocab")
public class VocabController {

    private final VocabService service;
    private final AuthenticatedUserResolver userResolver;

    public VocabController(VocabService service, AuthenticatedUserResolver userResolver) {
        this.service = service;
        this.userResolver = userResolver;
    }

    @PostMapping({"", "/"})
    @ResponseStatus(HttpStatus.CREATED)
    public VocabEntryResponse create(
            @AuthenticationPrincipal Jwt jwt,
            @Valid @RequestBody CreateVocabRequest request
    ) {
        return service.create(userResolver.requireUserId(jwt), request);
    }

    @PostMapping("/lookup")
    public VocabLookupResponse lookup(
            @AuthenticationPrincipal Jwt jwt,
            @Valid @RequestBody VocabLookupRequest request
    ) {
        return service.lookup(userResolver.requireUserId(jwt), request);
    }

    @PostMapping("/capture")
    public VocabEntryResponse capture(
            @AuthenticationPrincipal Jwt jwt,
            @Valid @RequestBody VocabCaptureRequest request
    ) {
        return service.capture(userResolver.requireUserId(jwt), request);
    }

    @GetMapping({"", "/"})
    public List<VocabEntryResponse> list(
            @AuthenticationPrincipal Jwt jwt,
            @RequestParam(required = false) VocabStatus status,
            @RequestParam(defaultValue = "0") @Min(0) int offset,
            @RequestParam(defaultValue = "50") @Min(1) @Max(200) int limit
    ) {
        return service.list(userResolver.requireUserId(jwt), status, offset, limit);
    }

    @GetMapping("/due")
    public List<VocabEntryResponse> due(
            @AuthenticationPrincipal Jwt jwt,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE_TIME) OffsetDateTime now,
            @RequestParam(defaultValue = "50") @Min(1) @Max(200) int limit
    ) {
        return service.due(userResolver.requireUserId(jwt), now, limit);
    }

    @PatchMapping("/{vocabId}")
    public VocabEntryResponse update(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable UUID vocabId,
            @Valid @RequestBody UpdateVocabRequest request
    ) {
        return service.update(userResolver.requireUserId(jwt), vocabId, request);
    }

    @PostMapping("/{vocabId}/review")
    public VocabEntryResponse review(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable UUID vocabId,
            @Valid @RequestBody ReviewVocabRequest request
    ) {
        return service.review(userResolver.requireUserId(jwt), vocabId, request);
    }

    @DeleteMapping("/{vocabId}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(
            @AuthenticationPrincipal Jwt jwt,
            @PathVariable UUID vocabId
    ) {
        service.delete(userResolver.requireUserId(jwt), vocabId);
    }
}
