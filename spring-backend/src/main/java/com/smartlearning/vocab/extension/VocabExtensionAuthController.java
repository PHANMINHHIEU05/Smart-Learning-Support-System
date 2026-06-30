package com.smartlearning.vocab.extension;

import com.smartlearning.auth.AuthenticatedUserResolver;
import jakarta.validation.Valid;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/vocab/extension")
public class VocabExtensionAuthController {

    private final VocabExtensionAuthService service;
    private final AuthenticatedUserResolver userResolver;

    public VocabExtensionAuthController(
            VocabExtensionAuthService service,
            AuthenticatedUserResolver userResolver
    ) {
        this.service = service;
        this.userResolver = userResolver;
    }

    @PostMapping("/pairing-codes")
    public CreatePairingCodeResponse createPairingCode(@AuthenticationPrincipal Jwt jwt) {
        return service.createPairingCode(userResolver.requireUserId(jwt));
    }

    @PostMapping("/exchange")
    public ExchangePairingCodeResponse exchangePairingCode(
            @Valid @RequestBody ExchangePairingCodeRequest request
    ) {
        return service.exchangePairingCode(request);
    }
}
