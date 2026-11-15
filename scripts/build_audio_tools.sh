#!/bin/sh
# Rebuild the bundled audio-only FFmpeg tools using unmodified pinned sources.
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work="$root/vendor/portable-tools"
export PATH="$work/w64devkit/bin;$PATH"
export PATH_SEPARATOR=';'
export ac_executable_extensions=.exe
export build_alias=x86_64-w64-mingw32
prefix="$work/prefix"
mkdir -p "$prefix" "$work/output"
cd "$work/lame-3.100"
if [ ! -f Makefile ]; then
    sh ./configure --build=x86_64-w64-mingw32 --host=x86_64-w64-mingw32 \
        --prefix="$prefix" --disable-shared --enable-static --disable-dependency-tracking \
        --disable-frontend --disable-nasm CC=gcc CFLAGS='-O2 -Wno-error=incompatible-pointer-types'
fi
make -j4
make install
cd "$work/ffmpeg-source"/*
printf '%s\n' 'n9.0.2-57-gd838f9f9ae' > VERSION
if [ ! -f ffbuild/config.mak ]; then
    sh ./configure --target-os=mingw32 --arch=x86_64 --cc=gcc --cxx=g++ \
        --disable-autodetect --disable-everything --disable-shared --enable-static \
        --disable-gpl --disable-nonfree --disable-version3 --disable-debug \
        --disable-doc --disable-ffplay --disable-avdevice --disable-swscale \
        --disable-x86asm --enable-w32threads --disable-pthreads \
        --enable-ffmpeg --enable-ffprobe --enable-avfilter --enable-swresample \
        --enable-network --enable-schannel --enable-libmp3lame \
        --enable-decoder=aac,aac_fixed,aac_latm,ac3,ac3_fixed,eac3,alac,flac,mp1,mp1float,mp2,mp2float,mp3,mp3float,opus,vorbis,wavpack,ape,pcm_s16le,pcm_s24le,pcm_s32le,pcm_u8,pcm_f32le,pcm_f64le \
        --enable-parser=aac,aac_latm,ac3,mpegaudio,opus,vorbis,flac \
        --enable-demuxer=aac,mp3,mov,matroska,ogg,wav,flac,hls,mpegts \
        --enable-muxer=mp3,ipod,adts,matroska,webm,mp4,ogg,wav \
        --enable-encoder=libmp3lame,pcm_s16le \
        --enable-bsf=aac_adtstoasc,mp3_header_decompress,extract_extradata \
        --enable-filter=aresample,aformat,anull,volume \
        --enable-protocol=file,http,https,tcp,tls,crypto \
        --extra-cflags='-I../../prefix/include' --extra-ldflags='-L../../prefix/lib -static-libgcc' \
        --extra-version=IDT-YT-audio
fi
make -j4 V=1
cp ffmpeg.exe ffprobe.exe "$work/output/"
./ffmpeg.exe -version
