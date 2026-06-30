package com.smartlearning.vocab.extension;

import com.smartlearning.tasks.JsonTestSupport;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.RequestPostProcessor;

import java.util.UUID;

import static org.hamcrest.Matchers.matchesPattern;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = "debug=false")
@AutoConfigureMockMvc
@ActiveProfiles("test")
class VocabExtensionAuthIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void pairingCodeExchangeReturnsExtensionTokenForVocabularyCapture() throws Exception {
        String userId = UUID.randomUUID().toString();
        String pairingCode = createPairingCode(userId);

        String exchangeResponse = mockMvc.perform(post("/api/v1/vocab/extension/exchange")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "pairing_code": "%s",
                                  "device_label": "Firefox local dev"
                                }
                                """.formatted(pairingCode)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.extension_token").isNotEmpty())
                .andExpect(jsonPath("$.token_type").value("Extension"))
                .andExpect(jsonPath("$.expires_at").isNotEmpty())
                .andReturn()
                .getResponse()
                .getContentAsString();
        String extensionToken = JsonTestSupport.extractString(exchangeResponse, "extension_token");

        mockMvc.perform(post("/api/v1/vocab/lookup")
                        .header(VocabExtensionTokenAuthenticationFilter.EXTENSION_TOKEN_HEADER, extensionToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "term": "pairing",
                                  "context_sentence": "Pairing removes token copy paste."
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.term").value("pairing"))
                .andExpect(jsonPath("$.already_saved").value(false));

        mockMvc.perform(post("/api/v1/vocab/capture")
                        .header(VocabExtensionTokenAuthenticationFilter.EXTENSION_TOKEN_HEADER, extensionToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "term": "pairing",
                                  "meaning": "ket noi thiet bi"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.user_id").value(userId))
                .andExpect(jsonPath("$.term").value("pairing"))
                .andExpect(jsonPath("$.meaning").value("ket noi thiet bi"));
    }

    @Test
    void pairingCodeCannotBeReused() throws Exception {
        String userId = UUID.randomUUID().toString();
        String pairingCode = createPairingCode(userId);

        exchangePairingCode(pairingCode)
                .andExpect(status().isOk());

        exchangePairingCode(pairingCode)
                .andExpect(status().isUnauthorized());
    }

    @Test
    void invalidExtensionTokenCannotAccessVocabularyCapture() throws Exception {
        mockMvc.perform(post("/api/v1/vocab/capture")
                        .header(VocabExtensionTokenAuthenticationFilter.EXTENSION_TOKEN_HEADER, "not-a-real-token")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "term": "blocked"
                                }
                                """))
                .andExpect(status().isUnauthorized());
    }

    private String createPairingCode(String userId) throws Exception {
        String response = mockMvc.perform(post("/api/v1/vocab/extension/pairing-codes")
                        .with(userJwt(userId)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.pairing_code", matchesPattern("[A-Z2-9]{4}-[A-Z2-9]{4}")))
                .andExpect(jsonPath("$.ttl_seconds").value(600))
                .andReturn()
                .getResponse()
                .getContentAsString();
        return JsonTestSupport.extractString(response, "pairing_code");
    }

    private org.springframework.test.web.servlet.ResultActions exchangePairingCode(String pairingCode) throws Exception {
        return mockMvc.perform(post("/api/v1/vocab/extension/exchange")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                        {
                          "pairing_code": "%s"
                        }
                        """.formatted(pairingCode)));
    }

    private static RequestPostProcessor userJwt(String userId) {
        return jwt().jwt(Jwt.withTokenValue("test-token")
                .header("alg", "none")
                .subject(userId)
                .build());
    }
}
