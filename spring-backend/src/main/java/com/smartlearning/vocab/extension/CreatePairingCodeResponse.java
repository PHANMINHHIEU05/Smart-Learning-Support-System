package com.smartlearning.vocab.extension;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.OffsetDateTime;

public record CreatePairingCodeResponse(
        @JsonProperty("pairing_code")
        String pairingCode,

        @JsonProperty("expires_at")
        OffsetDateTime expiresAt,

        @JsonProperty("ttl_seconds")
        long ttlSeconds
) {
}
