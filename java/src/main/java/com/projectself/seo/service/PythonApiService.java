package com.projectself.seo.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.multipart.MultipartFile;

@Service
@RequiredArgsConstructor
public class PythonApiService {
    
    @Value("${python.api.base-url}")
    private String pythonApiBaseUrl;
    
    private final RestTemplate restTemplate = new RestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();
    
    public JsonNode uploadDocument(MultipartFile file, String tenantId, String collectionName, String scope) throws Exception {
        String url = pythonApiBaseUrl + "/api/upload";
        
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        ByteArrayResource fileResource = new ByteArrayResource(file.getBytes()) {
            @Override
            public String getFilename() {
                return file.getOriginalFilename();
            }
        };
        body.add("file", fileResource);
        body.add("tenant_id", tenantId);
        body.add("collection_name", collectionName);
        body.add("scope", scope);
        
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);
        
        HttpEntity<MultiValueMap<String, Object>> request = new HttpEntity<>(body, headers);
        ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.POST, request, String.class);
        
        return objectMapper.readTree(response.getBody());
    }
    
    public JsonNode search(String query, String tenantId, String collectionName) throws Exception {
        String url = pythonApiBaseUrl + "/api/search";

        ObjectNode body = objectMapper.createObjectNode();
        body.put("query", query);
        body.put("tenant_id", tenantId);
        body.put("collection_name", collectionName);

        return exchangeJson(url, body);
    }

    
    public JsonNode generateTitles(String topic, String keywords, String tenantId, String collectionName, String llmProvider) throws Exception {
        String url = pythonApiBaseUrl + "/api/generate/titles";

        ObjectNode body = objectMapper.createObjectNode();
        body.put("topic", topic);
        body.put("keywords", keywords);
        body.put("tenant_id", tenantId);
        body.put("collection_name", collectionName);
        body.put("llm_provider", llmProvider);

        return exchangeJson(url, body);
    }

    public JsonNode generateOutlines(String threadId, String selectedTitle) throws Exception {
        String url = pythonApiBaseUrl + "/api/generate/outlines";

        ObjectNode body = objectMapper.createObjectNode();
        body.put("thread_id", threadId);
        body.put("selected_title", selectedTitle);

        return exchangeJson(url, body);
    }

    public JsonNode generateArticle(String threadId, String selectedOutline) throws Exception {
        String url = pythonApiBaseUrl + "/api/generate/article";

        ObjectNode body = objectMapper.createObjectNode();
        body.put("thread_id", threadId);
        body.put("selected_outline", selectedOutline);

        return exchangeJson(url, body);
    }

    private JsonNode exchangeJson(String url, ObjectNode body) throws Exception {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<String> request = new HttpEntity<>(objectMapper.writeValueAsString(body), headers);
        ResponseEntity<String> response = restTemplate.exchange(url, HttpMethod.POST, request, String.class);
        return objectMapper.readTree(response.getBody());
    }
}
