#include <stdio.h>
#include <stdint.h>
#include <string.h>

typedef struct
{
	uint8_t r;
	uint8_t g;
	uint8_t b;
} RGB_data_t;

#ifndef PIX_W
#define PIX_W 1280
#endif
#ifndef PIX_H
#define PIX_H 960
#endif

uint8_t image[PIX_H][PIX_W];

RGB_data_t _fb_base_ppm[PIX_H][PIX_W];

uint8_t img_bayer2rgb(uint32_t index)
{
	//set last byte to '\n'
	//GBRG bayer format
	//if index = 0 || 479 (first and last row)
	if (index == 0 || index == (PIX_H - 1))
	{
		//whole row zero
		memset(&_fb_base_ppm[index][0], 0, PIX_W * 3);
	}
	//check if index is odd : BG
	else if (index % 2 != 0)
	{
		//run for start from blue
		for (uint32_t raw_i = 0; raw_i < PIX_W; raw_i++)
		{
			//0th byte || (PIX_W - 1) byte
			if (raw_i == 0 || raw_i == (PIX_W - 1))
			{
				//all zero
				_fb_base_ppm[index][raw_i].r = 0;
				_fb_base_ppm[index][raw_i].g = 0;
				_fb_base_ppm[index][raw_i].b = 0;
			}
			//check if odd byte : Gb
			else if (raw_i % 2 != 0)
			{
				//red = vertical avg
				_fb_base_ppm[index][raw_i].r = (image[index - 1][raw_i] +
												image[index + 1][raw_i]) /
											   2;
				//green = reading
				_fb_base_ppm[index][raw_i].g = (image[index][raw_i] + image[index - 1][raw_i - 1] + image[index - 1][raw_i + 1] + image[index + 1][raw_i - 1] + image[index + 1][raw_i + 1]) / 5;
				//blue = horizontal avg
				_fb_base_ppm[index][raw_i].b = (image[index][raw_i - 1] + image[index][raw_i + 1]) / 2;
			}
			//if even : B
			else
			{
				//red = diagonal avg
				_fb_base_ppm[index][raw_i].r = (image[index - 1][raw_i - 1] + image[index - 1][raw_i + 1] + image[index + 1][raw_i - 1] + image[index + 1][raw_i + 1]) / 4;
				//green = vertical and horizontal avg
				_fb_base_ppm[index][raw_i].g = (image[index][raw_i - 1] + image[index][raw_i + 1] + image[index - 1][raw_i] + image[index + 1][raw_i]) / 4;
				//blue = reading
				_fb_base_ppm[index][raw_i].b = image[index][raw_i];
			}
		}
	}
	//else index is even : GR
	else
	{
		//run for start from green
		for (uint32_t raw_i = 0; raw_i < PIX_W; raw_i++)
		{
			//0th byte || (PIX_W - 1)th byte:
			if (raw_i == 0 || raw_i == (PIX_W - 1))
			{
				//all zeros
				_fb_base_ppm[index][raw_i].r = 0;
				_fb_base_ppm[index][raw_i].g = 0;
				_fb_base_ppm[index][raw_i].b = 0;
			}
			//check if odd byte : R
			else if (raw_i % 2 != 0)
			{
				//red = reading
				_fb_base_ppm[index][raw_i].r = image[index][raw_i];
				//green = horizontal and vertical avg
				_fb_base_ppm[index][raw_i].g = (image[index][raw_i - 1] + image[index][raw_i + 1] + image[index - 1][raw_i] + image[index + 1][raw_i]) / 4;
				//blue = diagonal avg
				_fb_base_ppm[index][raw_i].b = (image[index - 1][raw_i - 1] + image[index - 1][raw_i + 1] + image[index + 1][raw_i - 1] + image[index + 1][raw_i + 1]) / 4;
			}
			//if even : Gr
			else
			{
				//red = horizontal avg
				_fb_base_ppm[index][raw_i].r = (image[index][raw_i - 1] + image[index][raw_i + 1]) / 2;
				//green = reading + diagonal corner
				_fb_base_ppm[index][raw_i].g = (image[index][raw_i] + image[index - 1][raw_i - 1] + image[index - 1][raw_i + 1] + image[index + 1][raw_i - 1]

												+ image[index + 1][raw_i + 1]) /
											   5;
				//blue = vertical avg
				_fb_base_ppm[index][raw_i].b = (image[index - 1][raw_i] + image[index + 1][raw_i]) / 2;
			}
		}
	}

	return 0;
}

int main(int argc, char *argv[])

//  argv[1] - source file
//  argv[2] - destination file

{
	FILE *fileptr;

	// PIX_W = atoi(argv[3]);
	// PIX_H = atoi(argv[4]);

	// Check if file exists
	if ((fileptr = fopen(argv[1], "rb")) != NULL)
	{

		printf("Trying to convert \"%s\" to PPM [%dx%d]\n", argv[1], PIX_W, PIX_H);

		//Convert File to `image` array
		int i = 0;
		int j = 0;
		fread(image, 1, PIX_W * PIX_H, fileptr);
		fclose(fileptr);

		for (i = 0; i < PIX_H; i++)
		{
			img_bayer2rgb(i);
		}

		// Write headers
		fileptr = fopen(argv[2], "w");
		printf("Writing to %s\n", argv[2]);
		fprintf(fileptr, "P6\n%d %d\n255\n", PIX_W, PIX_H);

		// Append data
		int x = fwrite(_fb_base_ppm, sizeof(_fb_base_ppm), 1, fileptr);
		fclose(fileptr);
	}
	else
	{
		("%s does not exists\n", argv[1]);
	}
	return 0;
}
