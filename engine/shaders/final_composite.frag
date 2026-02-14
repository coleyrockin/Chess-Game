#version 330

in vec2 vUv;
out vec4 fragColor;

uniform sampler2D uScene;
uniform sampler2D uBloom;
uniform sampler2D uDepth;
uniform float uExposure;
uniform float uBloomStrength;
uniform float uTime;
uniform float uCameraSpeed;
uniform float uFocusDepth;
uniform float uDofStrength;
uniform float uMotionBlur;
uniform vec2 uResolution;

float random(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
}

vec3 tonemap(vec3 color, float exposure) {
    vec3 mapped = vec3(1.0) - exp(-color * exposure);
    return mapped;
}

float luma(vec3 c) {
    return dot(c, vec3(0.299, 0.587, 0.114));
}

vec3 fxaaApprox(vec2 uv) {
    vec2 texel = 1.0 / uResolution;
    vec3 c = texture(uScene, uv).rgb;
    vec3 n = texture(uScene, uv + vec2(0.0, texel.y)).rgb;
    vec3 s = texture(uScene, uv - vec2(0.0, texel.y)).rgb;
    vec3 e = texture(uScene, uv + vec2(texel.x, 0.0)).rgb;
    vec3 w = texture(uScene, uv - vec2(texel.x, 0.0)).rgb;
    float contrast = abs(luma(c) - luma(n)) + abs(luma(c) - luma(s)) + abs(luma(c) - luma(e)) + abs(luma(c) - luma(w));
    float edge = smoothstep(0.05, 0.26, contrast);
    vec3 avg = (n + s + e + w + c) / 5.0;
    return mix(c, avg, edge * 0.55);
}

vec3 applyMotionBlur(vec2 uv, float amount) {
    if (amount < 0.001) {
        return texture(uScene, uv).rgb;
    }
    vec2 center = vec2(0.5, 0.5);
    vec2 dir = normalize(uv - center + vec2(1e-5));
    vec2 texel = 1.0 / uResolution;
    vec3 accum = vec3(0.0);
    float total = 0.0;
    for (int i = -4; i <= 4; i++) {
        float w = 1.0 - (abs(float(i)) / 4.5);
        vec2 offset = dir * texel * float(i) * (3.0 + amount * 6.0);
        accum += texture(uScene, uv + offset).rgb * w;
        total += w;
    }
    return accum / max(total, 0.001);
}

void main() {
    vec2 uv = vUv;
    vec3 baseAA = fxaaApprox(uv);
    vec3 motionBlurred = applyMotionBlur(uv, clamp(uMotionBlur + (uCameraSpeed * 0.25), 0.0, 1.0));
    vec3 scene = mix(baseAA, motionBlurred, clamp(uMotionBlur, 0.0, 1.0));

    vec3 bloom = texture(uBloom, uv).rgb * uBloomStrength;
    float depth = texture(uDepth, uv).r;
    float focus = smoothstep(0.0, 1.0, abs(depth - uFocusDepth) * 3.2);
    float dof = clamp(focus * uDofStrength, 0.0, 1.0);

    vec2 texel = 1.0 / uResolution;
    vec3 dofBlur = vec3(0.0);
    dofBlur += texture(uScene, uv + vec2(texel.x, 0.0)).rgb;
    dofBlur += texture(uScene, uv - vec2(texel.x, 0.0)).rgb;
    dofBlur += texture(uScene, uv + vec2(0.0, texel.y)).rgb;
    dofBlur += texture(uScene, uv - vec2(0.0, texel.y)).rgb;
    dofBlur *= 0.25;

    vec3 colorOut = mix(scene + bloom, dofBlur + bloom, dof);

    mat3 grade = mat3(
        1.05, 0.02, -0.02,
        -0.01, 1.0, 0.02,
        0.05, 0.01, 0.95
    );
    colorOut = grade * colorOut;

    colorOut = tonemap(colorOut, uExposure);
    colorOut = pow(colorOut, vec3(1.0 / 2.2));

    float vignette = smoothstep(0.9, 0.28, length(uv - vec2(0.5)));
    colorOut *= mix(0.75, 1.0, vignette);

    float grain = (random(uv * uResolution * (1.0 + fract(uTime))) - 0.5) * 0.03;
    colorOut += grain;

    fragColor = vec4(colorOut, 1.0);
}
