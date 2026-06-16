package com.smartlearning.auth;

import org.springframework.security.oauth2.jwt.Jwt;

public record CurrentUserResponse(
        String userId,
        String email,
        String role
) {
    public static CurrentUserResponse from(Jwt jwt) {
        return new CurrentUserResponse(
                jwt.getSubject(),
                jwt.getClaimAsString("email"),
                jwt.getClaimAsString("role")
        );
    }
}
