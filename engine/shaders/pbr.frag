#version 330

struct Material {
    vec3 albedo;
    float metallic;
    float roughness;
    float specular;
    vec3 emissive;
};

struct DirectionalLight {
    vec3 direction;
    vec3 color;
    float intensity;
};

struct PointLight {
    vec3 position;
    vec3 color;
    float intensity;
    float range;
};

struct SpotLight {
    vec3 position;
    vec3 direction;
    vec3 color;
    float intensity;
    float cutoffCos;
    float range;
};

uniform Material uMaterial;
uniform DirectionalLight uDirLight;
uniform vec3 uAmbient;
uniform int uPointLightCount;
uniform PointLight uPointLights[8];
uniform int uSpotLightCount;
uniform SpotLight uSpotLights[2];
uniform vec3 uViewPos;
uniform sampler2D uShadowMap;
uniform samplerCube uSkybox;
uniform vec3 uFogColor;
uniform float uFogDensity;
uniform float uFogHeightFalloff;
uniform float uTime;

in vec3 vWorldPos;
in vec3 vNormal;
in vec2 vUv;
in vec4 vLightSpacePos;

layout (location = 0) out vec4 fragColor;
layout (location = 1) out vec4 brightColor;

float distributionGGX(vec3 N, vec3 H, float roughness) {
    float a = roughness * roughness;
    float a2 = a * a;
    float nDotH = max(dot(N, H), 0.0);
    float nDotH2 = nDotH * nDotH;
    float num = a2;
    float denom = (nDotH2 * (a2 - 1.0) + 1.0);
    denom = 3.14159 * denom * denom;
    return num / max(denom, 0.00001);
}

float geometrySchlickGGX(float nDotV, float roughness) {
    float r = roughness + 1.0;
    float k = (r * r) / 8.0;
    float num = nDotV;
    float denom = nDotV * (1.0 - k) + k;
    return num / max(denom, 0.00001);
}

float geometrySmith(vec3 N, vec3 V, vec3 L, float roughness) {
    float ggx1 = geometrySchlickGGX(max(dot(N, V), 0.0), roughness);
    float ggx2 = geometrySchlickGGX(max(dot(N, L), 0.0), roughness);
    return ggx1 * ggx2;
}

vec3 fresnelSchlick(float cosTheta, vec3 F0) {
    return F0 + (1.0 - F0) * pow(clamp(1.0 - cosTheta, 0.0, 1.0), 5.0);
}

float shadowFactor(vec4 lightSpacePos, vec3 normal, vec3 lightDir) {
    vec3 projCoords = lightSpacePos.xyz / max(lightSpacePos.w, 0.0001);
    projCoords = projCoords * 0.5 + 0.5;
    if (projCoords.z > 1.0 || projCoords.x < 0.0 || projCoords.x > 1.0 || projCoords.y < 0.0 || projCoords.y > 1.0) {
        return 0.0;
    }

    float bias = max(0.0012 * (1.0 - dot(normal, lightDir)), 0.0009);
    vec2 texelSize = 1.0 / vec2(textureSize(uShadowMap, 0));
    float shadow = 0.0;
    for (int x = -1; x <= 1; x++) {
        for (int y = -1; y <= 1; y++) {
            float pcfDepth = texture(uShadowMap, projCoords.xy + vec2(x, y) * texelSize).r;
            shadow += (projCoords.z - bias > pcfDepth) ? 1.0 : 0.0;
        }
    }
    shadow /= 9.0;
    return shadow;
}

vec3 shadePointLight(PointLight light, vec3 N, vec3 V, vec3 F0, vec3 albedo, float roughness, float metallic) {
    vec3 L = light.position - vWorldPos;
    float distance = length(L);
    if (distance > light.range) {
        return vec3(0.0);
    }
    L = normalize(L);
    vec3 H = normalize(V + L);
    float attenuation = 1.0 / (1.0 + (distance * distance) / max(light.range * light.range * 0.65, 0.001));
    vec3 radiance = light.color * light.intensity * attenuation;

    float NDF = distributionGGX(N, H, roughness);
    float G = geometrySmith(N, V, L, roughness);
    vec3 F = fresnelSchlick(max(dot(H, V), 0.0), F0);

    vec3 numerator = NDF * G * F;
    float denominator = 4.0 * max(dot(N, V), 0.0) * max(dot(N, L), 0.0) + 0.0001;
    vec3 specular = numerator / denominator;

    vec3 kS = F;
    vec3 kD = (vec3(1.0) - kS) * (1.0 - metallic);
    float NdotL = max(dot(N, L), 0.0);
    return (kD * albedo / 3.14159 + specular) * radiance * NdotL;
}

vec3 shadeSpotLight(SpotLight light, vec3 N, vec3 V, vec3 F0, vec3 albedo, float roughness, float metallic) {
    vec3 L = light.position - vWorldPos;
    float distance = length(L);
    if (distance > light.range) {
        return vec3(0.0);
    }
    L = normalize(L);
    float theta = dot(normalize(-light.direction), L);
    if (theta < light.cutoffCos) {
        return vec3(0.0);
    }

    float cone = smoothstep(light.cutoffCos, 1.0, theta);
    vec3 H = normalize(V + L);
    float attenuation = cone / (1.0 + (distance * distance) / max(light.range * light.range * 0.55, 0.001));
    vec3 radiance = light.color * light.intensity * attenuation;

    float NDF = distributionGGX(N, H, roughness);
    float G = geometrySmith(N, V, L, roughness);
    vec3 F = fresnelSchlick(max(dot(H, V), 0.0), F0);
    vec3 numerator = NDF * G * F;
    float denominator = 4.0 * max(dot(N, V), 0.0) * max(dot(N, L), 0.0) + 0.0001;
    vec3 specular = numerator / denominator;

    vec3 kS = F;
    vec3 kD = (vec3(1.0) - kS) * (1.0 - metallic);
    float NdotL = max(dot(N, L), 0.0);
    return (kD * albedo / 3.14159 + specular) * radiance * NdotL;
}

void main() {
    vec3 N = normalize(vNormal);
    vec3 V = normalize(uViewPos - vWorldPos);
    vec3 albedo = uMaterial.albedo;
    float metallic = clamp(uMaterial.metallic, 0.0, 1.0);
    float roughness = clamp(uMaterial.roughness, 0.04, 1.0);

    vec3 F0 = mix(vec3(0.04), albedo, metallic);

    vec3 Ld = normalize(-uDirLight.direction);
    vec3 Hd = normalize(V + Ld);
    float nDotL = max(dot(N, Ld), 0.0);

    float NDF = distributionGGX(N, Hd, roughness);
    float G = geometrySmith(N, V, Ld, roughness);
    vec3 F = fresnelSchlick(max(dot(Hd, V), 0.0), F0);
    vec3 specular = (NDF * G * F) / (4.0 * max(dot(N, V), 0.0) * max(nDotL, 0.0) + 0.0001);

    vec3 kS = F;
    vec3 kD = (vec3(1.0) - kS) * (1.0 - metallic);
    float shadow = shadowFactor(vLightSpacePos, N, Ld);

    vec3 direct = (kD * albedo / 3.14159 + specular) * (uDirLight.color * uDirLight.intensity) * nDotL * (1.0 - shadow);
    vec3 ambient = uAmbient * albedo;

    vec3 pointAccum = vec3(0.0);
    for (int i = 0; i < uPointLightCount; i++) {
        pointAccum += shadePointLight(uPointLights[i], N, V, F0, albedo, roughness, metallic);
    }

    vec3 spotAccum = vec3(0.0);
    for (int i = 0; i < uSpotLightCount; i++) {
        spotAccum += shadeSpotLight(uSpotLights[i], N, V, F0, albedo, roughness, metallic);
    }

    vec3 R = reflect(-V, N);
    vec3 env = texture(uSkybox, R).rgb;
    vec3 reflection = env * mix(0.15, 0.8, metallic) * (1.0 - roughness * 0.75);

    float rainFlicker = 0.96 + 0.04 * sin((vWorldPos.x + vWorldPos.z + uTime * 3.0) * 1.7);
    vec3 colorOut = (ambient + direct + pointAccum + spotAccum + reflection) * rainFlicker;
    float rim = pow(1.0 - max(dot(N, V), 0.0), 2.2);
    vec3 rimLight = uDirLight.color * rim * (0.08 + uMaterial.specular * 0.06);
    colorOut += rimLight;
    colorOut += uMaterial.emissive;

    float dist = length(uViewPos - vWorldPos);
    float heightFactor = clamp(exp(-max(vWorldPos.y - 0.25, 0.0) * uFogHeightFalloff), 0.0, 1.0);
    float fogAmount = 1.0 - exp(-dist * uFogDensity);
    fogAmount *= heightFactor;
    fogAmount = clamp(fogAmount * 0.82, 0.0, 1.0);

    vec3 fogged = mix(colorOut, uFogColor, clamp(fogAmount, 0.0, 1.0));
    fragColor = vec4(fogged, 1.0);

    float brightness = dot(fogged, vec3(0.2126, 0.7152, 0.0722));
    if (brightness > 1.0) {
        brightColor = vec4(fogged, 1.0);
    } else {
        brightColor = vec4(0.0, 0.0, 0.0, 1.0);
    }
}
