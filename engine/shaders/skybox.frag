#version 330

in vec3 vTexCoord;
out vec4 fragColor;

uniform samplerCube uSkybox;

void main() {
    vec3 c = texture(uSkybox, vTexCoord).rgb;
    fragColor = vec4(c, 1.0);
}
