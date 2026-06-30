package com.smartlearning.vocab.extension;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.OffsetDateTime;

public record ExchangePairingCodeResponse(
        @JsonProperty("extension_token")
        String extensionToken,

        @JsonProperty("expires_at")
        OffsetDateTime expiresAt,

        @JsonProperty("token_type")
        String tokenType
) {
}
