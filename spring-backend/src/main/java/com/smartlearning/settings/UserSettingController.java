package com.smartlearning.settings;

import com.smartlearning.auth.AuthenticatedUserResolver;
import jakarta.validation.Valid;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Validated
@RestController
@RequestMapping("/api/v1/settings")
public class UserSettingController {

    private final UserSettingService service;
    private final AuthenticatedUserResolver userResolver;

    public UserSettingController(UserSettingService service, AuthenticatedUserResolver userResolver) {
        this.service = service;
        this.userResolver = userResolver;
    }

    @GetMapping({"", "/"})
    public UserSettingResponse get(@AuthenticationPrincipal Jwt jwt) {
        return service.getOrCreate(userResolver.requireUserId(jwt));
    }

    @PutMapping({"", "/"})
    public UserSettingResponse update(
            @AuthenticationPrincipal Jwt jwt,
            @Valid @RequestBody UserSettingUpdateRequest request
    ) {
        return service.update(userResolver.requireUserId(jwt), request);
    }
}
