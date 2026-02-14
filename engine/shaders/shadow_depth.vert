#version 330

in vec3 in_position;

uniform mat4 uModel;
uniform mat4 uLightSpaceMatrix;

void main() {
    gl_Position = uLightSpaceMatrix * uModel * vec4(in_position, 1.0);
}
