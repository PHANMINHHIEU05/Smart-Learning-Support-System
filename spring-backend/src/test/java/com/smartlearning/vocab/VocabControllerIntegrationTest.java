package com.smartlearning.vocab;

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

import static org.hamcrest.Matchers.hasSize;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.jwt;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.patch;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@SpringBootTest(properties = "debug=false")
@AutoConfigureMockMvc
@ActiveProfiles("test")
class VocabControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void createListDueAndReviewVocabularyEntry() throws Exception {
        String userId = UUID.randomUUID().toString();

        String createResponse = mockMvc.perform(post("/api/v1/vocab/")
                        .with(userJwt(userId))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "term": "  resilient  ",
                                  "meaning": "co kha nang phuc hoi",
                                  "example_sentence": "She is resilient under pressure.",
                                  "source_type": "manual",
                                  "source_ref": "unit-test",
                                  "next_review_at": "2026-06-17T01:00:00Z"
                                }
                                """))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.vocab_id").isNotEmpty())
                .andExpect(jsonPath("$.user_id").value(userId))
                .andExpect(jsonPath("$.term").value("resilient"))
                .andExpect(jsonPath("$.status").value("not_started"))
                .andExpect(jsonPath("$.interval_days").value(0))
                .andExpect(jsonPath("$.repetition_count").value(0))
                .andExpect(jsonPath("$.next_review_at").value("2026-06-17T01:00:00Z"))
                .andReturn()
                .getResponse()
                .getContentAsString();

        String vocabId = JsonTestSupport.extractString(createResponse, "vocab_id");

        mockMvc.perform(get("/api/v1/vocab/?limit=20")
                        .with(userJwt(userId)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].vocab_id").value(vocabId));

        mockMvc.perform(get("/api/v1/vocab/?status=not_started&limit=20")
                        .with(userJwt(userId)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].vocab_id").value(vocabId));

        mockMvc.perform(get("/api/v1/vocab/due?now=2026-06-17T02:00:00Z&limit=10")
                        .with(userJwt(userId)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(1)))
                .andExpect(jsonPath("$[0].vocab_id").value(vocabId));

        mockMvc.perform(post("/api/v1/vocab/{vocabId}/review", vocabId)
                        .with(userJwt(userId))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "quality": "remembered",
                                  "reviewed_at": "2026-06-17T03:00:00Z"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.vocab_id").value(vocabId))
                .andExpect(jsonPath("$.status").value("remembered"))
                .andExpect(jsonPath("$.interval_days").value(1))
                .andExpect(jsonPath("$.repetition_count").value(1))
                .andExpect(jsonPath("$.last_reviewed_at").value("2026-06-17T03:00:00Z"))
                .andExpect(jsonPath("$.next_review_at").value("2026-06-18T03:00:00Z"));
    }

    @Test
    void rejectDuplicateTermForSameUser() throws Exception {
        String userId = UUID.randomUUID().toString();

        createWord(userId, "Apple")
                .andExpect(status().isCreated());

        createWord(userId, "apple")
                .andExpect(status().isConflict());
    }

    @Test
    void rejectCrossUserReviewAccess() throws Exception {
        String ownerId = UUID.randomUUID().toString();
        String otherUserId = UUID.randomUUID().toString();

        String createResponse = createWord(ownerId, "boundary")
                .andExpect(status().isCreated())
                .andReturn()
                .getResponse()
                .getContentAsString();
        String vocabId = JsonTestSupport.extractString(createResponse, "vocab_id");

        mockMvc.perform(post("/api/v1/vocab/{vocabId}/review", vocabId)
                        .with(userJwt(otherUserId))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "quality": "easy",
                                  "reviewed_at": "2026-06-17T03:00:00Z"
                                }
                                """))
                .andExpect(status().isNotFound());
    }

    @Test
    void rejectInvalidVocabularyPayloads() throws Exception {
        String userId = UUID.randomUUID().toString();

        mockMvc.perform(post("/api/v1/vocab/")
                        .with(userJwt(userId))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "term": "   "
                                }
                                """))
                .andExpect(status().isBadRequest());

        String createResponse = createWord(userId, "valid")
                .andExpect(status().isCreated())
                .andReturn()
                .getResponse()
                .getContentAsString();
        String vocabId = JsonTestSupport.extractString(createResponse, "vocab_id");

        mockMvc.perform(patch("/api/v1/vocab/{vocabId}", vocabId)
                        .with(userJwt(userId))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "term": "   "
                                }
                                """))
                .andExpect(status().isBadRequest());
    }

    @Test
    void lookupAndCaptureVocabularyFromFirefoxExtension() throws Exception {
        String userId = UUID.randomUUID().toString();

        mockMvc.perform(post("/api/v1/vocab/lookup")
                        .with(userJwt(userId))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "term": "consequence",
                                  "context_sentence": "Every action has a consequence.",
                                  "page_url": "https://example.com/article",
                                  "page_title": "English Reading"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.term").value("consequence"))
                .andExpect(jsonPath("$.normalized_term").value("consequence"))
                .andExpect(jsonPath("$.example_sentence").value("Every action has a consequence."))
                .andExpect(jsonPath("$.source_type").value("firefox_extension"))
                .andExpect(jsonPath("$.source_ref").value("https://example.com/article"))
                .andExpect(jsonPath("$.already_saved").value(false));

        String captureResponse = mockMvc.perform(post("/api/v1/vocab/capture")
                        .with(userJwt(userId))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "term": "consequence",
                                  "meaning": "ket qua",
                                  "translation_vi": "hậu quả",
                                  "definition_en": "a result of an action",
                                  "example_sentence": "Every action has a consequence.",
                                  "part_of_speech": "noun",
                                  "phonetic": "/test/",
                                  "audio_url": "https://audio.test/consequence.mp3",
                                  "dictionary_provider": "dictionaryapi.dev",
                                  "translation_provider": "mymemory",
                                  "page_url": "https://example.com/article",
                                  "page_title": "English Reading"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.vocab_id").isNotEmpty())
                .andExpect(jsonPath("$.term").value("consequence"))
                .andExpect(jsonPath("$.meaning").value("ket qua"))
                .andExpect(jsonPath("$.translation_vi").value("hậu quả"))
                .andExpect(jsonPath("$.definition_en").value("a result of an action"))
                .andExpect(jsonPath("$.part_of_speech").value("noun"))
                .andExpect(jsonPath("$.phonetic").value("/test/"))
                .andExpect(jsonPath("$.audio_url").value("https://audio.test/consequence.mp3"))
                .andExpect(jsonPath("$.source_type").value("firefox_extension"))
                .andExpect(jsonPath("$.source_ref").value("https://example.com/article"))
                .andExpect(jsonPath("$.status").value("not_started"))
                .andReturn()
                .getResponse()
                .getContentAsString();
        String vocabId = JsonTestSupport.extractString(captureResponse, "vocab_id");

        mockMvc.perform(post("/api/v1/vocab/lookup")
                        .with(userJwt(userId))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "term": "consequence"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.already_saved").value(true));

        mockMvc.perform(post("/api/v1/vocab/capture")
                        .with(userJwt(userId))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "term": "Consequence",
                                  "meaning": "duplicate should not create another row"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.vocab_id").value(vocabId))
                .andExpect(jsonPath("$.meaning").value("ket qua"))
                .andExpect(jsonPath("$.translation_vi").value("hậu quả"));
    }

    @Test
    void duplicateCaptureEnrichesMissingMetadata() throws Exception {
        String userId = UUID.randomUUID().toString();

        String createResponse = mockMvc.perform(post("/api/v1/vocab/capture")
                        .with(userJwt(userId))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "term": "adaptive"
                                }
                                """))
                .andExpect(status().isOk())
                .andReturn()
                .getResponse()
                .getContentAsString();
        String vocabId = JsonTestSupport.extractString(createResponse, "vocab_id");

        mockMvc.perform(post("/api/v1/vocab/capture")
                        .with(userJwt(userId))
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("""
                                {
                                  "term": "Adaptive",
                                  "meaning": "có khả năng thích nghi",
                                  "translation_vi": "thích nghi",
                                  "definition_en": "able to change for new conditions",
                                  "part_of_speech": "adjective",
                                  "phonetic": "/əˈdæp.tɪv/"
                                }
                                """))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.vocab_id").value(vocabId))
                .andExpect(jsonPath("$.meaning").value("có khả năng thích nghi"))
                .andExpect(jsonPath("$.translation_vi").value("thích nghi"))
                .andExpect(jsonPath("$.definition_en").value("able to change for new conditions"))
                .andExpect(jsonPath("$.part_of_speech").value("adjective"))
                .andExpect(jsonPath("$.phonetic").value("/əˈdæp.tɪv/"));
    }

    @Test
    void deleteVocabularyEntryForCurrentUser() throws Exception {
        String userId = UUID.randomUUID().toString();

        String createResponse = createWord(userId, "temporary")
                .andExpect(status().isCreated())
                .andReturn()
                .getResponse()
                .getContentAsString();
        String vocabId = JsonTestSupport.extractString(createResponse, "vocab_id");

        mockMvc.perform(delete("/api/v1/vocab/{vocabId}", vocabId)
                        .with(userJwt(userId)))
                .andExpect(status().isNoContent());

        mockMvc.perform(get("/api/v1/vocab/?limit=20")
                        .with(userJwt(userId)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$", hasSize(0)));
    }

    private org.springframework.test.web.servlet.ResultActions createWord(String userId, String term) throws Exception {
        return mockMvc.perform(post("/api/v1/vocab/")
                .with(userJwt(userId))
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                        {
                          "term": "%s",
                          "meaning": "sample meaning"
                        }
                        """.formatted(term)));
    }

    private static RequestPostProcessor userJwt(String userId) {
        return jwt().jwt(Jwt.withTokenValue("test-token")
                .header("alg", "none")
                .subject(userId)
                .build());
    }
}
