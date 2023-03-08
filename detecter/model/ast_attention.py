import torch
import math
import logging

logger = logging.getLogger("ast_attention")

class AttentionLayer(torch.nn.Module):

    def __init__(self, hidden_size: int, num_heads: int=1) -> None:
        super().__init__()
        self.num_heads = num_heads
        self.hidden_size = hidden_size
        self.attn = torch.nn.MultiheadAttention(hidden_size, num_heads=num_heads)
        self.norm = torch.nn.LayerNorm(hidden_size)
        self.drop = torch.nn.Dropout(p=0.3)
    
    def forward(self, input: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        B, L, _ = mask.shape
        assert(mask.shape == (B, L, L))
        assert(input.shape == (L, B, self.hidden_size))

        output, _ = self.attn(
            input, input, input, attn_mask=mask.repeat_interleave(self.num_heads, dim=0))
        output = self.norm(output)
        return input + self.drop(output)


class FCLayer(torch.nn.Module):

    def __init__(self, hidden_size: int) -> None:
        super().__init__()
        self.w1 = torch.nn.Linear(hidden_size, hidden_size * 2)
        self.w2 = torch.nn.Linear(hidden_size * 2, hidden_size)
        self.drop = torch.nn.Dropout(p=0.3)

    def forward(self, input: torch.Tensor) -> torch.Tensor:
        hidden = torch.relu(self.w1(input))
        output = self.w2(hidden)
        return input + self.drop(output)


class EncodeLayer(torch.nn.Module):

    def __init__(self, hidden_size: int, num_heads: int) -> None:
        super().__init__()
        self.attn = AttentionLayer(hidden_size, num_heads)
        self.fc = FCLayer(hidden_size)
    
    def forward(self, input: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        return self.fc(self.attn(input, mask))


class AstAttention(torch.nn.Module):
    
    def __init__(self, input_size: int, hidden_size: int, num_layers: int, num_heads: int = 1) -> None:
        super().__init__()

        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.dense = torch.nn.Linear(input_size, hidden_size)
        self.layers = torch.nn.ModuleList([
            EncodeLayer(hidden_size, num_heads)
            for _ in range(num_layers)
        ])
        self.norm = torch.nn.LayerNorm(hidden_size)

    def forward(self, input: torch.Tensor, mask: torch.Tensor):
        N, B, _ = input.shape

        assert(input.shape == (N, B, self.input_size))

        hidden = self.dense(input)
        for layer in self.layers:
            hidden = layer(hidden, mask)
            # logger.debug("hidden {}".format(hidden))

        output = self.norm(hidden)
        output = torch.sum(output, dim=0, keepdim=False)
        return output