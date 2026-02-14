#version 330

in vec3 in_position;
out vec3 vTexCoord;

uniform mat4 uView;
uniform mat4 uProjection;

void main() {
    vTexCoord = in_position;
    mat4 view = mat4(mat3(uView));
    vec4 pos = uProjection * view * vec4(in_position, 1.0);
    gl_Position = pos.xyww;
}
