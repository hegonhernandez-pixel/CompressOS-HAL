// Bounded, one-shot Vulkan 1.0 RLE worker. No kernel memory or swap access.
#include <vulkan/vulkan.h>
#include "rle_shader.h"
#include <array>
#include <algorithm>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <vector>

static constexpr uint32_t page_size = 4096;
static constexpr uint32_t max_input = 1024 * 1024;
static void check(VkResult result) {
    if (result != VK_SUCCESS) throw std::runtime_error("Vulkan error " + std::to_string(result));
}
struct Buffer {
    VkBuffer handle = VK_NULL_HANDLE;
    VkDeviceMemory memory = VK_NULL_HANDLE;
    void* mapped = nullptr;
};
struct Runtime {
    VkInstance instance = VK_NULL_HANDLE;
    VkDevice device = VK_NULL_HANDLE;
    VkDescriptorSetLayout descriptor_layout = VK_NULL_HANDLE;
    VkPipelineLayout layout = VK_NULL_HANDLE;
    VkShaderModule shader = VK_NULL_HANDLE;
    VkPipeline pipeline = VK_NULL_HANDLE;
    VkDescriptorPool descriptors = VK_NULL_HANDLE;
    VkCommandPool commands = VK_NULL_HANDLE;
    VkFence fence = VK_NULL_HANDLE;
    std::array<Buffer, 2> buffers{};
    ~Runtime() {
        if (device) {
            if (fence) vkDestroyFence(device, fence, nullptr);
            if (commands) vkDestroyCommandPool(device, commands, nullptr);
            if (pipeline) vkDestroyPipeline(device, pipeline, nullptr);
            if (shader) vkDestroyShaderModule(device, shader, nullptr);
            if (layout) vkDestroyPipelineLayout(device, layout, nullptr);
            if (descriptors) vkDestroyDescriptorPool(device, descriptors, nullptr);
            if (descriptor_layout) vkDestroyDescriptorSetLayout(device, descriptor_layout, nullptr);
            for (auto& buffer : buffers) {
                if (buffer.mapped) vkUnmapMemory(device, buffer.memory);
                if (buffer.handle) vkDestroyBuffer(device, buffer.handle, nullptr);
                if (buffer.memory) vkFreeMemory(device, buffer.memory, nullptr);
            }
            vkDestroyDevice(device, nullptr);
        }
        if (instance) vkDestroyInstance(instance, nullptr);
    }
    void allocate(Buffer& buffer, VkDeviceSize size, VkPhysicalDevice physical) {
        VkBufferCreateInfo info{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
        info.size = size;
        info.usage = VK_BUFFER_USAGE_STORAGE_BUFFER_BIT;
        info.sharingMode = VK_SHARING_MODE_EXCLUSIVE;
        check(vkCreateBuffer(device, &info, nullptr, &buffer.handle));
        VkMemoryRequirements requirements{};
        vkGetBufferMemoryRequirements(device, buffer.handle, &requirements);
        VkPhysicalDeviceMemoryProperties properties{};
        vkGetPhysicalDeviceMemoryProperties(physical, &properties);
        uint32_t type = properties.memoryTypeCount;
        const auto flags = VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT | VK_MEMORY_PROPERTY_HOST_COHERENT_BIT;
        for (uint32_t i = 0; i < properties.memoryTypeCount; ++i) {
            if ((requirements.memoryTypeBits & (1u << i)) &&
                (properties.memoryTypes[i].propertyFlags & flags) == flags) { type = i; break; }
        }
        if (type == properties.memoryTypeCount) throw std::runtime_error("no coherent host-visible storage memory");
        VkMemoryAllocateInfo allocation{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
        allocation.allocationSize = requirements.size;
        allocation.memoryTypeIndex = type;
        check(vkAllocateMemory(device, &allocation, nullptr, &buffer.memory));
        check(vkBindBufferMemory(device, buffer.handle, buffer.memory, 0));
        check(vkMapMemory(device, buffer.memory, 0, size, 0, &buffer.mapped));
    }
    std::vector<uint32_t> run(const std::vector<uint8_t>& input) {
        const uint32_t size = static_cast<uint32_t>(input.size());
        const uint32_t pages = (size + page_size - 1) / page_size;
        const VkDeviceSize output_size = VkDeviceSize(pages) * 4097 * sizeof(uint32_t);
        const VkDeviceSize input_size = VkDeviceSize(size) * sizeof(uint32_t);
        VkApplicationInfo application{VK_STRUCTURE_TYPE_APPLICATION_INFO};
        application.pApplicationName = "CompressOS-HAL experimental RLE";
        application.apiVersion = VK_API_VERSION_1_0;
        VkInstanceCreateInfo instance_info{VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO};
        instance_info.pApplicationInfo = &application;
        check(vkCreateInstance(&instance_info, nullptr, &instance));
        uint32_t count = 0;
        check(vkEnumeratePhysicalDevices(instance, &count, nullptr));
        std::vector<VkPhysicalDevice> devices(count);
        check(vkEnumeratePhysicalDevices(instance, &count, devices.data()));
        VkPhysicalDevice physical = VK_NULL_HANDLE;
        uint32_t family = 0;
        // Prefer real GPUs over software devices, but allow lavapipe for validation.
        std::stable_sort(devices.begin(), devices.end(), [](auto a, auto b) {
            VkPhysicalDeviceProperties pa{}, pb{};
            vkGetPhysicalDeviceProperties(a, &pa); vkGetPhysicalDeviceProperties(b, &pb);
            return (pa.deviceType == VK_PHYSICAL_DEVICE_TYPE_CPU) < (pb.deviceType == VK_PHYSICAL_DEVICE_TYPE_CPU);
        });
        for (auto candidate : devices) {
            VkPhysicalDeviceProperties properties{};
            vkGetPhysicalDeviceProperties(candidate, &properties);
            const auto& limits = properties.limits;
            if (limits.maxStorageBufferRange < std::max(input_size, output_size) ||
                limits.maxComputeWorkGroupInvocations < 64 || limits.maxComputeWorkGroupSize[0] < 64 ||
                limits.maxComputeWorkGroupCount[0] < (pages + 63) / 64) continue;
            uint32_t families = 0;
            vkGetPhysicalDeviceQueueFamilyProperties(candidate, &families, nullptr);
            std::vector<VkQueueFamilyProperties> queues(families);
            vkGetPhysicalDeviceQueueFamilyProperties(candidate, &families, queues.data());
            for (uint32_t i = 0; i < families; ++i) {
                if (queues[i].queueCount && (queues[i].queueFlags & VK_QUEUE_COMPUTE_BIT)) {
                    physical = candidate; family = i; break;
                }
            }
            if (physical) break;
        }
        if (!physical) throw std::runtime_error("no suitable Vulkan compute device");
        VkPhysicalDeviceProperties selected{};
        vkGetPhysicalDeviceProperties(physical, &selected);
        std::cerr << "device: " << selected.deviceName << '\n';
        float priority = 1.0f;
        VkDeviceQueueCreateInfo queue_info{VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO};
        queue_info.queueFamilyIndex = family; queue_info.queueCount = 1; queue_info.pQueuePriorities = &priority;
        VkDeviceCreateInfo device_info{VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO};
        device_info.queueCreateInfoCount = 1; device_info.pQueueCreateInfos = &queue_info;
        check(vkCreateDevice(physical, &device_info, nullptr, &device));
        VkQueue queue;
        vkGetDeviceQueue(device, family, 0, &queue);
        allocate(buffers[0], input_size, physical);
        allocate(buffers[1], output_size, physical);
        auto* mapped_input = static_cast<uint32_t*>(buffers[0].mapped);
        for (uint32_t i = 0; i < size; ++i) mapped_input[i] = input[i];
        std::memset(buffers[1].mapped, 0, output_size);
        std::array<VkDescriptorSetLayoutBinding, 2> bindings{};
        for (uint32_t i = 0; i < 2; ++i) {
            bindings[i].binding = i; bindings[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER;
            bindings[i].descriptorCount = 1; bindings[i].stageFlags = VK_SHADER_STAGE_COMPUTE_BIT;
        }
        VkDescriptorSetLayoutCreateInfo descriptor_info{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO};
        descriptor_info.bindingCount = 2; descriptor_info.pBindings = bindings.data();
        check(vkCreateDescriptorSetLayout(device, &descriptor_info, nullptr, &descriptor_layout));
        VkPushConstantRange push{VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(size)};
        VkPipelineLayoutCreateInfo layout_info{VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO};
        layout_info.setLayoutCount = 1; layout_info.pSetLayouts = &descriptor_layout;
        layout_info.pushConstantRangeCount = 1; layout_info.pPushConstantRanges = &push;
        check(vkCreatePipelineLayout(device, &layout_info, nullptr, &layout));
        VkShaderModuleCreateInfo shader_info{VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO};
        shader_info.codeSize = sizeof(shader_code); shader_info.pCode = shader_code;
        check(vkCreateShaderModule(device, &shader_info, nullptr, &shader));
        VkComputePipelineCreateInfo pipeline_info{VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO};
        pipeline_info.stage.sType = VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        pipeline_info.stage.stage = VK_SHADER_STAGE_COMPUTE_BIT;
        pipeline_info.stage.module = shader; pipeline_info.stage.pName = "main"; pipeline_info.layout = layout;
        check(vkCreateComputePipelines(device, VK_NULL_HANDLE, 1, &pipeline_info, nullptr, &pipeline));
        VkDescriptorPoolSize pool_size{VK_DESCRIPTOR_TYPE_STORAGE_BUFFER, 2};
        VkDescriptorPoolCreateInfo pool_info{VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO};
        pool_info.maxSets = 1; pool_info.poolSizeCount = 1; pool_info.pPoolSizes = &pool_size;
        check(vkCreateDescriptorPool(device, &pool_info, nullptr, &descriptors));
        VkDescriptorSetAllocateInfo set_info{VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO};
        set_info.descriptorPool = descriptors; set_info.descriptorSetCount = 1; set_info.pSetLayouts = &descriptor_layout;
        VkDescriptorSet set;
        check(vkAllocateDescriptorSets(device, &set_info, &set));
        std::array<VkDescriptorBufferInfo, 2> buffer_info{{{buffers[0].handle, 0, input_size},
                                                       {buffers[1].handle, 0, output_size}}};
        std::array<VkWriteDescriptorSet, 2> writes{};
        for (uint32_t i = 0; i < 2; ++i) {
            writes[i].sType = VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET; writes[i].dstSet = set;
            writes[i].dstBinding = i; writes[i].descriptorCount = 1;
            writes[i].descriptorType = VK_DESCRIPTOR_TYPE_STORAGE_BUFFER; writes[i].pBufferInfo = &buffer_info[i];
        }
        vkUpdateDescriptorSets(device, 2, writes.data(), 0, nullptr);
        VkCommandPoolCreateInfo command_info{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};
        command_info.queueFamilyIndex = family;
        check(vkCreateCommandPool(device, &command_info, nullptr, &commands));
        VkCommandBufferAllocateInfo allocate_info{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
        allocate_info.commandPool = commands; allocate_info.level = VK_COMMAND_BUFFER_LEVEL_PRIMARY; allocate_info.commandBufferCount = 1;
        VkCommandBuffer command;
        check(vkAllocateCommandBuffers(device, &allocate_info, &command));
        VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
        check(vkBeginCommandBuffer(command, &begin));
        vkCmdBindPipeline(command, VK_PIPELINE_BIND_POINT_COMPUTE, pipeline);
        vkCmdBindDescriptorSets(command, VK_PIPELINE_BIND_POINT_COMPUTE, layout, 0, 1, &set, 0, nullptr);
        vkCmdPushConstants(command, layout, VK_SHADER_STAGE_COMPUTE_BIT, 0, sizeof(size), &size);
        vkCmdDispatch(command, (pages + 63) / 64, 1, 1);
        VkMemoryBarrier barrier{VK_STRUCTURE_TYPE_MEMORY_BARRIER};
        barrier.srcAccessMask = VK_ACCESS_SHADER_WRITE_BIT; barrier.dstAccessMask = VK_ACCESS_HOST_READ_BIT;
        vkCmdPipelineBarrier(command, VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT, VK_PIPELINE_STAGE_HOST_BIT,
                             0, 1, &barrier, 0, nullptr, 0, nullptr);
        check(vkEndCommandBuffer(command));
        VkFenceCreateInfo fence_info{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
        check(vkCreateFence(device, &fence_info, nullptr, &fence));
        VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};
        submit.commandBufferCount = 1; submit.pCommandBuffers = &command;
        check(vkQueueSubmit(queue, 1, &submit, fence));
        const auto waited = vkWaitForFences(device, 1, &fence, VK_TRUE, 10'000'000'000ULL);
        if (waited != VK_SUCCESS) {
            // Pending device work must not be destroyed. End this isolated worker;
            // the OS/driver owns teardown. Python also enforces a process deadline.
            std::cerr << "compute completion failed: " << waited << std::endl;
            std::_Exit(2);
        }
        auto* output = static_cast<uint32_t*>(buffers[1].mapped);
        return {output, output + output_size / sizeof(uint32_t)};
    }
};
static void write_le(uint32_t value) {
    for (int i = 0; i < 4; ++i) std::cout.put(static_cast<char>((value >> (8 * i)) & 255));
}
int main() {
    try {
        std::vector<uint8_t> input;
        char value;
        while (std::cin.get(value)) {
            if (input.size() == max_input) throw std::runtime_error("input exceeds 1 MiB");
            input.push_back(static_cast<uint8_t>(value));
        }
        if (!std::cin.eof()) throw std::runtime_error("input read failed");
        if (input.empty()) return 0;
        Runtime runtime;
        for (auto word : runtime.run(input)) write_le(word);
        return std::cout ? 0 : 2;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 2;
    }
}
