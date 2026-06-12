/***************************************************************************
                   instance_generator.cpp  -  description
                             -------------------
    begin                : Wed May 28 2014
    copyright            : (C) 2014 by Christian Blum
    email                : christian.c.blum@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/

using namespace std;

#ifdef HAVE_CONFIG_H
#include <config.h>
#endif

#include <vector>
#include <string>
#include <stdio.h>
#include <stdlib.h>
#include <iostream>
#include <string.h>
#include <fstream>
#include <sstream>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <algorithm>
#include <set>
#include <map>
#include <random>
#include <chrono>

vector<int> sequence_length_vec;
vector<int> asize_vec;
int reps = 10;


inline int stoi(string &s) {

  return atoi(s.c_str());
}

inline double stof(string &s) {

  return atof(s.c_str());
}

void read_parameters(int argc, char **argv) {

    int iarg=1;
    while (iarg < argc) {
        if (strcmp(argv[iarg],"-reps")==0) reps = atoi(argv[++iarg]);
        else if (strcmp(argv[iarg],"-len")==0) {
            int len = atoi(argv[++iarg]);
            sequence_length_vec.push_back(len);
        }
        else if (strcmp(argv[iarg],"-asize")==0) {
            int asize = atoi(argv[++iarg]);
            asize_vec.push_back(asize);
        }
        iarg++;
    }
}

int random_int(int max, double rnum) {

    int res = int(rnum * max);
    if (res == max) res = res - 1;
    return res;
}

int random_letter_index(map<int,double>& pmap, double wheel) {

    map<int,double>::iterator mait = pmap.begin();
    double ws = 0.0;
    while (ws < wheel and mait != pmap.end()) {
        ws += mait->second;
        ++mait;
    }
    --mait;
    return mait->first;
}


/**********
Main function
**********/

int main( int argc, char **argv ) {

    if ( argc < 3 ) {
        cout << "Use: greedy -i <input_file> ..." << endl;
        exit(1);
    }
    else read_parameters(argc,argv);

    // initializes the random number generator
    unsigned seed = std::chrono::system_clock::now().time_since_epoch().count();
    std::default_random_engine generator(seed);
    std::uniform_real_distribution<double> standard_distribution(0.0,1.0);

    for (int i3 = 0; i3 < int(asize_vec.size()); ++i3) {
        int asize = asize_vec[i3];

        //fill the map containing the alphabet
        vector<char> vmap(asize);
        if (asize <= 32) {
            // Caso original: solo letras desde 'A'
            for (int i = 0; i < asize; ++i) {
                vmap[i] = char('A' + i);
            }
        } else {
            // Caso extendido: caracteres ASCII imprimibles
            // Rango de 95 símbolos visibles (32 a 126)
            if (asize > 95) {
                cerr << "Error: máximo 95 caracteres distintos en ASCII visible." << endl;
                exit(1);
            }
            for (int i = 0; i < asize; ++i) {
                vmap[i] = char(32 + i);   // desde ' ' hasta '~'
            }
        }
        //equal probabilities for letters
        vector<double> pmap(asize);
        for (int i = 0; i < asize; ++i) pmap[i] = 1.0/double(asize);

        for (int i2 = 0; i2 < int(sequence_length_vec.size()); ++i2) {
            int m = sequence_length_vec[i2];
                    for (int k = 1; k <= reps; ++k) {

                        ofstream myfile;
                        ostringstream ss;
                        ss << "len_" << m << "_sigma" << asize << "_" << k << ".txt";
                        myfile.open((ss.str()).c_str());

                            for (int j = 0; j < m; ++j) {
                                std::discrete_distribution<> distr(pmap.begin(), pmap.end());
                                myfile << vmap[distr(generator)];
                            }
                            myfile << endl;
                        myfile.close();
                    }
        }
    }
}
