#version 330

in vec2 vUv;
out vec4 fragColor;

uniform sampler2D uImage;
uniform bool uHorizontal;

void main() {
    vec2 texOffset = 1.0 / vec2(textureSize(uImage, 0));
    float kernel[5] = float[](0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);

    vec3 result = texture(uImage, vUv).rgb * kernel[0];
    for (int i = 1; i < 5; i++) {
        vec2 offset = uHorizontal ? vec2(texOffset.x * i, 0.0) : vec2(0.0, texOffset.y * i);
        result += texture(uImage, vUv + offset).rgb * kernel[i];
        result += texture(uImage, vUv - offset).rgb * kernel[i];
    }
    fragColor = vec4(result, 1.0);
}
