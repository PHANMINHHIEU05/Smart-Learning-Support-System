package com.smartlearning.vocab.extension;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record ExchangePairingCodeRequest(
        @JsonProperty("pairing_code")
        @NotBlank
        @Size(max = 32)
        String pairingCode,

        @JsonProperty("device_label")
        @Size(max = 120)
        String deviceLabel
) {
}
