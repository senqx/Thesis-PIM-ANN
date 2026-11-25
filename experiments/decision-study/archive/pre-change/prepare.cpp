// Native preparation for all policies; input is an explicit integer CSR matrix.
// Build: g++ -O3 -std=c++17 prepare.cpp -o prepare
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iostream>
#include <map>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>
#include <sys/resource.h>
using U=uint32_t; using Bytes=std::vector<uint8_t>;
struct Matrix {U n,m,z;std::vector<U> p,c,w;};
struct Plan {Bytes meta;std::vector<U> permutation;bool reordered=false;};
void word(Bytes &b,U v){for(int k=0;k<4;k++)b.push_back((v>>(8*k))&255);}
void setword(Bytes&b,size_t p,U v){for(int k=0;k<4;k++)b[p+k]=(v>>(8*k))&255;}
void pad(Bytes&b,U n=8){while(b.size()%n)b.push_back(0);}
Matrix load(const std::string& name){
    std::ifstream f(name,std::ios::binary);if(!f)throw std::runtime_error("input");
    auto read=[&](){uint8_t b[4];f.read((char*)b,4);if(!f)throw std::runtime_error("short input");return U(b[0])|(U(b[1])<<8)|(U(b[2])<<16)|(U(b[3])<<24);};
    Matrix a;a.n=read();a.m=read();a.z=read();
    for(U i=0;i<=a.n;i++)a.p.push_back(read());
    for(U i=0;i<a.z;i++)a.c.push_back(read());
    for(U i=0;i<a.z;i++)a.w.push_back(read());return a;
}
Plan prepare(const Matrix&a,const std::string&mode,U bytes){
    Plan q;q.permutation.resize(a.m);std::iota(q.permutation.begin(),q.permutation.end(),0);
    if(mode=="hot"){
        q.reordered=true;
        std::vector<U> counts(a.m);for(U c:a.c)counts[c]++;
        std::sort(q.permutation.begin(),q.permutation.end(),[&](U x,U y){return counts[x]!=counts[y]?counts[x]>counts[y]:x<y;});
    }
    if(mode=="stream128"||mode=="stream512"||mode=="hot"||mode=="full"){
        std::vector<U> inv(a.m);for(U i=0;i<a.m;i++)inv[q.permutation[i]]=i;
        for(U p:a.p)word(q.meta,p);pad(q.meta,32);
        for(U i=0;i<a.z;i++){word(q.meta,inv[a.c[i]]);word(q.meta,a.w[i]);}
    }else if(mode=="batch"){
        U groups=a.n/4;q.meta.resize(((groups+1)*4+15)/16*16);
        for(U g=0;g<groups;g++){
            setword(q.meta,g*4,q.meta.size());
            std::vector<U> ids,weights;Bytes slots;
            auto flush=[&](){
                if(slots.empty())return;
                word(q.meta,ids.size());word(q.meta,slots.size());
                for(U id:ids)word(q.meta,id);pad(q.meta);
                for(U w:weights)word(q.meta,w);pad(q.meta);
                q.meta.insert(q.meta.end(),slots.begin(),slots.end());pad(q.meta);
                ids.clear();weights.clear();slots.clear();
            };
            for(U r=0;r<4;r++)for(U i=a.p[4*g+r];i<a.p[4*g+r+1];i++){
                auto it=std::find(ids.begin(),ids.end(),a.c[i]);
                if(slots.size()==64||(it==ids.end()&&ids.size()==std::min(U(64),U(512/bytes)))){flush();it=ids.end();}
                U slot=it-ids.begin();if(it==ids.end())ids.push_back(a.c[i]);
                weights.push_back(a.w[i]);slots.push_back((r<<6)|slot);
            }flush();
        }setword(q.meta,groups*4,q.meta.size());
    }else{
        U b=mode=="bcsr2"?2:4,groups=a.n/b;
        q.meta.resize(((groups+1)*4+15)/16*16);
        for(U g=0;g<groups;g++){
            setword(q.meta,g*4,q.meta.size());std::map<U,std::vector<U>> blocks;
            for(U r=0;r<b;r++)for(U i=a.p[g*b+r];i<a.p[g*b+r+1];i++){
                auto &v=blocks[a.c[i]/b];if(v.empty())v.resize(b*b);
                v[r*b+a.c[i]%b]=a.w[i];
            }
            for(const auto&entry:blocks){word(q.meta,entry.first*b);word(q.meta,0);for(U w:entry.second)word(q.meta,w);}
        }setword(q.meta,groups*4,q.meta.size());
    }return q;
}
Bytes source_values(const Matrix&a,U words,U bytes,U epoch){
    Bytes b;b.reserve(a.m*bytes);
    for(U id=0;id<a.m;id++){for(U f=0;f<words;f++)word(b,(id*17+f*13+3+epoch*7)%19+1);while(b.size()%bytes)word(b,0);}return b;
}
Bytes refresh(const Plan&q,const Bytes&values,U bytes){
    if(!q.reordered)return values;
    Bytes b(values.size());
    for(U i=0;i<q.permutation.size();i++)std::memcpy(b.data()+i*bytes,values.data()+q.permutation[i]*bytes,bytes);
    return b;
}
void save(const std::string&n,const Bytes&b){std::ofstream f(n,std::ios::binary);f.write((const char*)b.data(),b.size());if(!f)throw std::runtime_error("write");}
std::array<uint64_t,5> inspect(const Matrix&a,const Plan&q,const std::string&mode,U words,U bytes,U t){
    std::vector<uint64_t> reads(t),calls(t),products(t);
    auto at=[&](U pos){return U(q.meta[pos])|(U(q.meta[pos+1])<<8)|(U(q.meta[pos+2])<<16)|(U(q.meta[pos+3])<<24);};
    auto rounded=[](U n){return (n+7)/8*8;};
    U capacity=(65536-49152-t*(512+5*bytes+32)-2048)/2048*2048;
    U hot=std::min(a.m,capacity/bytes);
    if(mode=="hot"||mode=="full")for(U p=0;p<hot*bytes;p+=2048){reads[(p/2048)%t]+=std::min(U(2048),hot*bytes-p);calls[(p/2048)%t]++;}
    for(U first=0;first<a.n;first+=4){
        U tid=(first/4)%t;
        if(mode=="batch"){
            reads[tid]+=16;calls[tid]++;
            for(U p=at(first);p<at(first+4);){
                U u=at(p),n=at(p+4);U size=8+rounded(4*u)+rounded(4*n)+rounded(n);
                reads[tid]+=size+u*bytes;calls[tid]+=4+u;products[tid]+=n*words;p+=size;
            }
        }else if(mode=="bcsr2"||mode=="bcsr4"){
            U b=mode=="bcsr2"?2:4;
            for(U rr=0;rr<4;rr+=b){
                U g=(first+rr)/b;reads[tid]+=16;calls[tid]++;
                for(U p=at(g*4);p<at(g*4+4);p+=8+4*b*b){
                    reads[tid]+=8+4*b*b+b*bytes;calls[tid]+=3;
                    for(U k=0;k<b*b;k++)if(at(p+8+k*4))products[tid]+=words;
                }
            }
        }else{
            reads[tid]+=32;calls[tid]++;U base=((a.n+1)*4+31)/32*32;
            for(U r=first;r<first+4;r++){
                U n=a.p[r+1]-a.p[r],chunk=mode=="stream128"?16:64;
                reads[tid]+=n*8;calls[tid]+=(n+chunk-1)/chunk;products[tid]+=n*words;
                for(U p=a.p[r];p<a.p[r+1];p++)if(mode.find("stream")==0||(mode=="hot"&&at(base+8*p)>=hot)){reads[tid]+=bytes;calls[tid]++;}
            }
        }
    }
    return {1,*std::max_element(products.begin(),products.end()),std::accumulate(reads.begin(),reads.end(),uint64_t(0))/8,*std::max_element(calls.begin(),calls.end()),uint64_t(a.n)*words};
}
int main(int argc,char**argv){
    if(argc!=9)return 2;Matrix a=load(argv[1]);std::string mode=argv[2],prefix=argv[6];
    U words=std::stoul(argv[3]),bytes=std::stoul(argv[4]),epoch=std::stoul(argv[5]),samples=std::stoul(argv[7]);
    U tasklets=std::stoul(argv[8]);
    auto values=source_values(a,words,bytes,epoch);
    auto q=prepare(a,mode,bytes);auto x=refresh(q,values,bytes);
    save(prefix+".meta",q.meta);save(prefix+".features",x);
    auto features=inspect(a,q,mode,words,bytes,tasklets);
    std::ofstream metrics(prefix+".metrics.json");metrics<<"[";for(U k=0;k<5;k++)metrics<<(k?",":"")<<features[k];metrics<<"]\n";
    std::ofstream out(prefix+".timings.csv");out<<"sample,prepare_ns,inspect_ns,refresh_ns\n";
    volatile size_t consume=0;
    for(U s=0;s<samples+3;s++){
        auto t0=std::chrono::steady_clock::now();auto p=prepare(a,mode,bytes);
        auto t1=std::chrono::steady_clock::now();auto f=inspect(a,p,mode,words,bytes,tasklets);
        auto t2=std::chrono::steady_clock::now();auto y=refresh(p,values,bytes);
        auto t3=std::chrono::steady_clock::now();consume+=p.meta.size()+y.size()+f[2];
        if(s>=3)out<<s-3<<","<<std::chrono::duration_cast<std::chrono::nanoseconds>(t1-t0).count()<<","<<std::chrono::duration_cast<std::chrono::nanoseconds>(t2-t1).count()<<","<<std::chrono::duration_cast<std::chrono::nanoseconds>(t3-t2).count()<<"\n";
    }
    struct rusage usage;getrusage(RUSAGE_SELF,&usage);
    std::cout<<"{\"process_peak_rss_kib\":"<<usage.ru_maxrss<<",\"metadata_bytes\":"<<q.meta.size()<<",\"feature_bytes\":"<<x.size()<<"}\n";
    return consume==0;
}
