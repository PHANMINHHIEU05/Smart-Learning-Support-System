package com.smartlearning.vocab;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.Size;
import org.hibernate.validator.constraints.Length;
import org.hibernate.validator.constraints.NotBlank;

public record VocabLookupRequest(
        @NotBlank
        @Length(max = 255)
        String term,

        @JsonProperty("context_sentence")
        @Size(max = 1000)
        String contextSentence,

        @JsonProperty("page_url")
        @Size(max = 2000)
        String pageUrl,

        @JsonProperty("page_title")
        @Size(max = 255)
        String pageTitle
) {
}
